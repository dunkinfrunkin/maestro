---
sidebar_position: 4
title: Disabled (Dev Only)
---

# Disabled Authentication

For local development and testing, you can disable authentication entirely. This skips all OIDC flows and allows unauthenticated access to the dashboard and API.

**Do not use this in production.**

## Configuration

```yaml
# config.yaml
auth:
  disabled: true
```

Or via environment variable:

```bash
MAESTRO_AUTH_DISABLED=true
```

Or via Docker:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_AUTH_DISABLED=true \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

## When to use

- Local development when you don't want to set up an OIDC provider
- Automated testing
- Quick demos

## What changes

- No login screen is shown
- All API requests are allowed without a JWT
- A default user is used for any operations that require a user context
- `MAESTRO_SECRET` is still required (for internal token signing) but no OIDC settings are needed
