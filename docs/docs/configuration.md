---
sidebar_position: 7
title: Configuration
---

# Configuration

Maestro can be configured through multiple layers. Each layer overrides the one below it, so you can set broad defaults and override specific values where needed.

## Configuration priority

Settings are resolved in this order (highest priority first):

| Priority | Source | Where it lives | Best for |
|---|---|---|---|
| 1 | CLI flags | `maestro serve --port 9000` | One-off overrides |
| 2 | Environment variables | Shell, `.env` file, Docker `-e` | Secrets, CI/CD, containers |
| 3 | config.yaml | `~/.maestro/config.yaml` | Local dev defaults |
| 4 | Dashboard UI | Settings pages in the browser | Per-workspace config (connections, agents, models) |
| 5 | Hardcoded defaults | Built into Maestro | Fallback values |

## config.yaml

The primary configuration file for local development. Generate it with:

```bash
maestro init
```

This creates `~/.maestro/config.yaml`:

```yaml
# Server
server:
  host: 127.0.0.1
  port: 8000

# Frontend
frontend:
  port: 3000

# Worker
worker:
  concurrency: 3
  poll_interval: 2.0
  mode: inline          # "inline" or "queue"

# Database
database:
  url: ""               # postgresql+asyncpg://user:pass@host:5432/db

# Authentication
auth:
  secret: ""            # Required. Generate with: openssl rand -hex 32
  disabled: false       # Set true to skip auth (dev only)
  oidc_issuer: ""       # e.g. https://yourcompany.okta.com/oauth2/default
  oidc_client_id: ""
  oidc_client_secret: ""

# Encryption
encryption:
  key: ""               # Fernet key for encrypting stored tokens

# Frontend URL (for CORS and redirects)
frontend_url: ""        # e.g. http://localhost:3000

# API keys (can also be set per-workspace in Settings > Models)
anthropic:
  api_key: ""

openai:
  api_key: ""
```

## Environment variables

Every config.yaml field maps to an environment variable. Environment variables take priority over config.yaml.

| Variable | config.yaml path | Description |
|---|---|---|
| `DATABASE_URL` | `database.url` | PostgreSQL connection string |
| `MAESTRO_SECRET` | `auth.secret` | JWT signing secret (required) |
| `MAESTRO_AUTH_DISABLED` | `auth.disabled` | Skip auth entirely (dev only) |
| `MAESTRO_OIDC_ISSUER` | `auth.oidc_issuer` | OIDC provider URL |
| `MAESTRO_OIDC_CLIENT_ID` | `auth.oidc_client_id` | OAuth client ID |
| `MAESTRO_OIDC_CLIENT_SECRET` | `auth.oidc_client_secret` | OAuth client secret |
| `MAESTRO_ENCRYPTION_KEY` | `encryption.key` | Fernet key for token encryption |
| `MAESTRO_FRONTEND_URL` | `frontend_url` | Frontend URL for CORS |
| `MAESTRO_WORKER_MODE` | `worker.mode` | `inline` or `queue` |
| `MAESTRO_CORS_ORIGINS` | - | Comma-separated allowed origins |
| `ANTHROPIC_API_KEY` | `anthropic.api_key` | Claude API key |
| `OPENAI_API_KEY` | `openai.api_key` | OpenAI API key |
| `POSTGRES_HOST` | - | PostgreSQL host (Docker mode) |
| `POSTGRES_PORT` | - | PostgreSQL port (Docker mode) |
| `POSTGRES_DB` | - | Database name (Docker mode) |
| `POSTGRES_USER` | - | Database user (Docker mode) |
| `POSTGRES_PASSWORD` | - | Database password (Docker mode) |
| `PORT` | - | Port to expose (Docker mode) |

## .env file

For local development, you can use a `.env` file instead of exporting variables:

```bash
cd backend
cp .env.example .env.local
```

Load it with:

```bash
maestro serve --env-file .env.local
```

Or source it manually:

```bash
set -a && source .env.local && set +a
maestro serve
```

The `.env` file has the lowest priority - it won't override variables already set in the environment or config.yaml.

## Docker

When running via Docker (`maestro app`, `maestro serve`, `maestro worker`), pass environment variables with `-e`:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  ghcr.io/dunkinfrunkin/maestro:latest
```

The Go CLI automatically passes through all `MAESTRO_*`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`, and `POSTGRES_*` environment variables to the Docker container.

## Dashboard UI

Some settings are configured through the dashboard rather than files:

### Connections

Configured in **Settings > Connections**. Stored encrypted in the database.

- GitHub, GitLab, Linear, Jira tokens and endpoints
- Per-connection repository/project scoping

See [Integrations](/docs/integrations) for setup details.

### Agent configuration

Configured in **Settings > Agents** per workspace.

| Setting | Where | What it controls |
|---|---|---|
| Enabled/disabled | Per agent toggle | Whether this agent runs in the pipeline |
| Model | Per agent dropdown | Which LLM model to use |
| Provider | Per agent dropdown | Anthropic or OpenAI |
| System prompt | Per agent editor | Custom instructions for the agent |

### Model selection

Each agent can use a different model. Configure per-workspace in **Settings > Models** or per-agent in the agent settings.

| Agent | Default model | Notes |
|---|---|---|
| Implementation | `claude-sonnet-4-6` | Needs strong coding ability |
| Review | `claude-sonnet-4-6` | Needs to reason about code quality |
| Risk Profile | `claude-haiku-4-5` | Lighter task, faster model works well |
| Deployment | None | No LLM needed |
| Monitor | `claude-haiku-4-5` | Reads logs and metrics |

### API keys

API keys can be set at two levels:

- **Global** - via config.yaml or environment variables (applies to all workspaces)
- **Per-workspace** - via **Settings > Models** in the dashboard (overrides global)

## Authentication

Maestro supports SSO via any OpenID Connect provider.

| Provider | OIDC issuer value |
|---|---|
| Okta | `https://yourcompany.okta.com/oauth2/default` |
| Google | `https://accounts.google.com` |
| Azure AD | `https://login.microsoftonline.com/{tenant-id}/v2.0` |

Set `MAESTRO_AUTH_DISABLED=true` to skip auth entirely (development only).

## Worker configuration

Workers can be tuned via config.yaml, CLI flags, or environment variables:

```yaml
# config.yaml
worker:
  concurrency: 3        # max parallel agent jobs
  poll_interval: 2.0    # seconds between queue polls
  mode: queue            # "inline" (in API process) or "queue" (separate workers)
```

```bash
# CLI flags override config.yaml
maestro worker --concurrency 5 --poll-interval 1.0
```

In production with separate workers, set `mode: queue` so the API server dispatches jobs to the queue instead of running agents inline.
