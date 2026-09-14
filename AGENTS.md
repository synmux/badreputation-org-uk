# Agent Guide for badreputation-org-uk

This document provides essential context and instructions for AI agents working in this repository.

## Project Overview

This is a **static website** project for [badreputation.org.uk](https://badreputation.org.uk).
It is primarily designed to be hosted on **Cloudflare Workers** (using the `assets` binding for static content), with a secondary configuration for containerized deployment using **Caddy**.

The content appears to be a static export of a WordPress site, organized by date (year/month).

## Tech Stack

- **Runtime/Package Manager**: Node.js 24.20.0+, `pnpm`
- **Deployment**: [Cloudflare Workers](https://workers.cloudflare.com/) via [Wrangler](https://developers.cloudflare.com/workers/wrangler/)
- **Containerization**: [Docker](https://www.docker.com/) + [Caddy](https://caddyserver.com/)
- **Linting**: [Trunk](https://trunk.io/)

## Key Commands

### Development & Deployment

| Command           | Description                                           |
| ----------------- | ----------------------------------------------------- |
| `pnpm run dev`    | Start local development server (wraps `wrangler dev`) |
| `pnpm run start`  | Alias for `dev`                                       |
| `pnpm run deploy` | Deploy to Cloudflare Workers                          |

### Docker

To build and test the Caddy-based container:

```bash
docker build -t badreputation .
docker run -p 8000:8000 badreputation
# Check http://localhost:8000
```

## Directory Structure

- **`public/`**: Contains the static website assets (HTML, images, CSS).
  - Organized by year/month (e.g., `public/2012/10/`).
  - Contains legacy WordPress paths (`wp-json/`, `wp-content/`).
- **`test/`**: Unit tests verifying configuration and file structure.
- **`.trunk/`**: Configuration for Trunk linter.
- **`wrangler.jsonc`**: Cloudflare Workers configuration (routes, asset directory).
- **`Caddyfile`**: Configuration for the Caddy web server (port 8000).

## Configuration Details

- **Cloudflare**:
  - Project Name: `badreputation-org-uk`
  - Routes: `badreputation.org.uk`, `www.badreputation.org.uk`
  - Compatibility Date: `2025-09-27`
  - Assets Directory: `./public`

- **Docker/Caddy**:
  - Base Image: `caddy:2.11.0-beta.1-alpine`
  - Exposes port `8000`
  - Serves static files from `/srv` (mapped from `public/`)

## Important Notes

1. **Static Content**: This repo hosts static HTML. There is no dynamic backend code or build step for the HTML itself (it's pre-generated).
2. **Private Package**: `package.json` is marked `"private": true` to prevent accidental npm publication.
3. **No CI Pipeline**: Currently, there is no standard CI/CD workflow file (e.g., `ci.yml`) visible in `.github/workflows/`, though AI agent workflows exist.
