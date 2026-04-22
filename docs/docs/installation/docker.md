---
sidebar_position: 2
title: Docker
---

# Docker

Run Maestro directly with Docker without installing the CLI. This is the best option for production deployments, CI/CD pipelines, and container orchestrators like Kubernetes.

## Quick start

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

Dashboard at [localhost:3000](http://localhost:3000).

## With external PostgreSQL

By default, the container expects a PostgreSQL instance. Use Docker Compose for a complete setup:

```bash
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro
docker compose up -d
```

This starts PostgreSQL on port 5432. Then run Maestro pointing to it:

```bash
docker run -d --name maestro \
  -p 3000:3000 \
  --network maestro_default \
  -e MAESTRO_SECRET=$(openssl rand -hex 32) \
  -e DATABASE_URL=postgresql+asyncpg://maestro:maestro@postgres:5432/maestro \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest
```

## Running the worker separately

For production, run the API and worker as separate containers:

```bash
# API + frontend
docker run -d --name maestro-api \
  -p 3000:3000 \
  -e MAESTRO_SECRET=your-secret \
  -e MAESTRO_WORKER_MODE=queue \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  ghcr.io/dunkinfrunkin/maestro:latest

# Worker (can run multiple)
docker run -d --name maestro-worker \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e MAESTRO_ENCRYPTION_KEY=your-fernet-key \
  ghcr.io/dunkinfrunkin/maestro:latest \
  maestro worker --concurrency 3
```

## Docker Compose (production)

For a full production setup with separate API and worker services:

```bash
cp .env.production.example .env
# fill in secrets
docker compose -f docker-compose.prod.yml up --build
```

## What the container includes

The Docker image is a multi-stage build containing:

- Python 3.12 backend (FastAPI + uvicorn)
- Node.js 22 frontend (Next.js standalone build)
- Nginx reverse proxy (port 3000)
- Claude Code CLI and OpenAI Codex CLI (for agent execution)
- Git (for repo cloning)
- Alembic (runs migrations on startup)

## Image tags

| Tag | Description |
|---|---|
| `latest` | Most recent release |
| `v0.35.4` | Specific version |

Images are published to `ghcr.io/dunkinfrunkin/maestro` on every release.

## Environment variables

All configuration is via environment variables when running in Docker. See [Configuration](/docs/configuration) for the full list.

Key variables:

| Variable | Required | Description |
|---|---|---|
| `MAESTRO_SECRET` | Yes | JWT signing secret |
| `ANTHROPIC_API_KEY` | Yes* | Claude API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `DATABASE_URL` | No | PostgreSQL connection string |
| `MAESTRO_AUTH_DISABLED` | No | Skip auth (dev only) |

*At least one of `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is required.
