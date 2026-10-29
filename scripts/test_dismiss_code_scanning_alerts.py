import unittest

from dismiss_code_scanning_alerts import retry_wait_seconds


class RetryWaitSecondsTest(unittest.TestCase):
    def test_success_and_client_errors_are_not_retried(self):
        self.assertIsNone(retry_wait_seconds(404, {}, "Not Found", 0))
        self.assertIsNone(retry_wait_seconds(422, {}, "Validation Failed", 0))

    def test_plain_403_is_a_permissions_error(self):
        self.assertIsNone(
            retry_wait_seconds(403, {}, "Resource not accessible by integration", 0)
        )

    def test_retry_after_header_wins(self):
        self.assertEqual(retry_wait_seconds(403, {"retry-after": "42"}, "", 0), 42)

    def test_exhausted_primary_limit_waits_until_reset(self):
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1100"}
        self.assertEqual(
            retry_wait_seconds(403, headers, "API rate limit exceeded", 1000), 101
        )

    def test_reset_in_the_past_still_waits_a_second(self):
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "900"}
        self.assertEqual(retry_wait_seconds(403, headers, "", 1000), 1)

    def test_secondary_limit_without_headers_waits_a_minute(self):
        self.assertEqual(
            retry_wait_seconds(403, {}, "You have exceeded a secondary rate limit", 0),
            60,
        )
        self.assertEqual(retry_wait_seconds(429, {}, "", 0), 60)

    def test_gateway_errors_retry_quickly(self):
        self.assertEqual(retry_wait_seconds(502, {}, "", 0), 5)


if __name__ == "__main__":
    unittest.main()
