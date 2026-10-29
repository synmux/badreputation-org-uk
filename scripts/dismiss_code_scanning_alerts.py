#!/usr/bin/env python3
"""Bulk-dismiss open GitHub code scanning alerts for a single rule.

Each run lists the alerts that are still open and dismisses them, so it is safe
to re-run after an interruption. Rate limits pause every worker until GitHub
says to resume, then carry on.

Usage:
    GITHUB_TOKEN=... ./scripts/dismiss_code_scanning_alerts.py [--dry-run]
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

API_ROOT = "https://api.github.com"
DEFAULT_COMMENT = "Static WordPress export; DOM XSS findings are not actionable."


def retry_wait_seconds(status, headers, body, now):
    """Seconds to wait before retrying a failed request, or None if it should not be retried."""
    if status in (502, 503, 504):
        return 5
    if status not in (403, 429):
        return None
    retry_after = headers.get("retry-after")
    if retry_after:
        return int(retry_after)
    if headers.get("x-ratelimit-remaining") == "0":
        return max(int(headers.get("x-ratelimit-reset", now)) - int(now), 0) + 1
    # Secondary rate limits without retry-after: GitHub asks for at least a minute.
    if status == 429 or "rate limit" in body.lower():
        return 60
    return None  # A plain 403 is a permissions problem.


class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.lock = threading.Lock()
        self.resume_at = 0.0

    def request(self, method, path, payload=None):
        while True:
            with self.lock:
                delay = self.resume_at - time.time()
            if delay > 0:
                time.sleep(delay)
            request = urllib.request.Request(
                API_ROOT + path,
                method=method,
                data=json.dumps(payload).encode() if payload is not None else None,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                body = error.read().decode(errors="replace")
                wait = retry_wait_seconds(error.code, error.headers, body, time.time())
                if wait is None:
                    raise RuntimeError(f"{method} {path} -> HTTP {error.code}: {body}") from error
                with self.lock:
                    if time.time() + wait > self.resume_at:
                        self.resume_at = time.time() + wait
                        print(f"HTTP {error.code}; pausing all workers for {wait}s", file=sys.stderr, flush=True)


def open_alert_numbers(client, repo, rule):
    """Collect every open alert number for the rule before mutating anything, so paging stays stable."""
    alert_numbers = []
    page = 1
    while True:
        batch = client.request("GET", f"/repos/{repo}/code-scanning/alerts?state=open&per_page=100&page={page}")
        if not batch:
            return alert_numbers
        alert_numbers += [alert["number"] for alert in batch if alert["rule"]["id"] == rule]
        page += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="synmux/badreputation-org-uk", help="owner/name")
    parser.add_argument("--rule", default="js/xss-through-dom", help="code scanning rule id to dismiss")
    parser.add_argument("--comment", default=DEFAULT_COMMENT, help="dismissal comment (max 280 chars)")
    parser.add_argument("--workers", type=int, default=8, help="concurrent dismiss requests")
    parser.add_argument("--dry-run", action="store_true", help="list matching alerts without dismissing")
    arguments = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")

    client = GitHubClient(token)
    alert_numbers = open_alert_numbers(client, arguments.repo, arguments.rule)
    print(f"{len(alert_numbers)} open {arguments.rule} alerts in {arguments.repo}", flush=True)
    if arguments.dry_run or not alert_numbers:
        return

    payload = {"state": "dismissed", "dismissed_reason": "won't fix", "dismissed_comment": arguments.comment}
    failures = []
    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures = {
            executor.submit(
                client.request, "PATCH", f"/repos/{arguments.repo}/code-scanning/alerts/{number}", payload
            ): number
            for number in alert_numbers
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()
            except Exception as error:  # Keep going; a re-run picks up anything left open.
                failures.append(futures[future])
                print(f"alert {futures[future]}: {error}", file=sys.stderr, flush=True)
            if completed % 100 == 0 or completed == len(futures):
                print(f"{completed}/{len(futures)} processed, {len(failures)} failed", flush=True)

    if failures:
        sys.exit(f"{len(failures)} alerts failed; re-run to retry them")


if __name__ == "__main__":
    main()
