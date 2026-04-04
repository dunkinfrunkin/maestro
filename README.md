# Maestro

Autonomous coding agent orchestration for engineering teams.

Maestro manages a pipeline of AI agents that implement, review, risk-assess, deploy, and monitor code changes — triggered from your issue tracker.

## Quick Start

Pull and run:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

Or with OpenAI (Codex CLI):

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

Open http://localhost:3000.

## How It Works

```
Issue → Implement → Review ↔ Fix → Risk Profile → Deploy → Monitor
```

Five dedicated agents, each with a single responsibility:

| Agent | What it does |
|---|---|
| **Implement** | Reads your codebase, writes code, runs tests, opens a PR |
| **Review** | Posts inline comments on specific lines (GitHub PRs and GitLab MRs), requests changes or approves |
| **Risk Profile** | Scores the PR across 7 dimensions, auto-approves low risk |
| **Deploy** | Verifies CI checks, merges via squash |
| **Monitor** | Watches Datadog and Splunk for 15 minutes post-deploy |

Agents communicate through PR comment threads — the same workflow as human developers.

## Authentication

Maestro supports SSO via any OpenID Connect provider.

### Okta

1. In Okta Admin, create a new App Integration (OIDC, Web)
2. Set the redirect URI: `http://localhost:3000/auth/callback`
3. Run with your Okta credentials:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e MAESTRO_OIDC_ISSUER=https://yourcompany.okta.com/oauth2/default \
  -e MAESTRO_OIDC_CLIENT_ID=your-client-id \
  -e MAESTRO_OIDC_CLIENT_SECRET=your-client-secret \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

### Google

1. In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), create OAuth 2.0 credentials (Web application)
2. Add redirect URI: `http://localhost:3000/auth/callback`
3. Run:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e MAESTRO_OIDC_ISSUER=https://accounts.google.com \
  -e MAESTRO_OIDC_CLIENT_ID=your-client-id.apps.googleusercontent.com \
  -e MAESTRO_OIDC_CLIENT_SECRET=your-client-secret \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

### Azure AD / Entra ID

```bash
-e MAESTRO_OIDC_ISSUER=https://login.microsoftonline.com/{tenant-id}/v2.0
-e MAESTRO_OIDC_CLIENT_ID=your-application-client-id
-e MAESTRO_OIDC_CLIENT_SECRET=your-client-secret
```

### Disable auth (development only)

```bash
-e MAESTRO_AUTH_DISABLED=true
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MAESTRO_SECRET` | Yes | JWT signing secret. Generate: `openssl rand -hex 32` |

> \* At least one of `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is required. You can also configure API keys per-workspace in **Settings > Models**.
| `ANTHROPIC_API_KEY` | * | Claude API key — powers agents using Claude CLI |
| `OPENAI_API_KEY` | * | OpenAI API key — powers agents using Codex CLI |
| `MAESTRO_OIDC_ISSUER` | No | OIDC provider URL for SSO |
| `MAESTRO_OIDC_CLIENT_ID` | No | OAuth client ID |
| `MAESTRO_OIDC_CLIENT_SECRET` | No | OAuth client secret |
| `MAESTRO_ENCRYPTION_KEY` | No | Fernet key for encrypting stored tokens |
| `MAESTRO_AUTH_DISABLED` | No | Set `true` to skip auth entirely |
| `POSTGRES_HOST` | No | External postgres host (default: embedded) |
| `POSTGRES_PORT` | No | Postgres port (default: `5432`) |
| `POSTGRES_DB` | No | Database name (default: `maestro`) |
| `POSTGRES_USER` | No | Database user (default: `maestro`) |
| `POSTGRES_PASSWORD` | No | Database password (default: `maestro`) |
| `PORT` | No | Port to expose (default: `3000`) |

## Connections

Maestro integrates with four platforms:

| Platform | Type | What it does |
|---|---|---|
| **GitHub** | Code host + issues | PRs, reviews, inline comments, CI checks |
| **GitLab** | Code host + issues | MRs, discussions, pipelines |
| **Linear** | Issue tracker | Sync issues from Linear projects |
| **Jira** | Issue tracker | Sync issues from Jira Cloud or Server |

Configure connections from **Settings > Connections** in the dashboard.

## Development

```bash
# Start postgres
docker compose up -d

# Backend
cd backend
cp .env.example .env.local   # fill in your keys
set -a && source .env.local && set +a
uv sync
uv run uvicorn maestro.app:app --reload --port 8000

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Dashboard at http://localhost:3000, API at http://localhost:8000.

## Docker Compose (production)

For running with an external postgres:

```bash
cp .env.production.example .env
# fill in secrets
docker compose -f docker-compose.prod.yml up --build
```

## Stack

- **Backend**: Python / FastAPI / PostgreSQL / SQLAlchemy
- **Frontend**: Next.js 16 / TypeScript / Tailwind CSS
- **Agents**: Claude Code CLI + OpenAI Codex CLI (configurable provider and model per agent)
- **Auth**: OIDC/SSO (Okta, Google, Azure AD) or email-only
- **Integrations**: GitHub, GitLab, Linear, Jira

## License

MIT
