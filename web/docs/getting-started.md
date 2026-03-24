---
sidebar_position: 1
title: Getting Started
---

# Getting Started

Get Maestro running locally in under 5 minutes.

## Prerequisites

| Requirement | Purpose |
|---|---|
| Docker + Docker Compose | PostgreSQL database |
| Python 3.11+ and [uv](https://docs.astral.sh/uv/) | Backend API |
| Node.js 20+ and npm | Frontend dashboard |
| Claude API key or [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | Agent execution |

## 1. Clone the repository

```bash
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro
```

## 2. Start the database

```bash
docker compose up -d
```

Starts PostgreSQL on port 5432. Default credentials are in `docker-compose.yml`.

## 3. Start the backend

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your API keys (see [Configuration](/docs/configuration) for all options), then:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

## 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard opens at [localhost:3000](http://localhost:3000).

## 5. Create your first task

1. Open the dashboard and select a project
2. Click **New Task**
3. Enter a title and description — for example:
   - **Title:** `Add health check endpoint`
   - **Description:** `Create a GET /health route that returns {"status": "ok"}`
4. Click **Queue Task**

The task enters the pipeline and flows through each stage automatically. You can watch it happen in real time from the task detail page.

## What happens next

Once queued, five agents take over in sequence:

1. **Implementation** — reads your codebase, writes code, runs tests, opens a PR
2. **Review** — posts inline comments on specific lines, requests changes or approves
3. **Risk Profile** — scores the PR across seven dimensions, auto-approves if low risk
4. **Deployment** — verifies CI checks, merges via squash
5. **Monitor** — watches Datadog and Splunk for 15 minutes post-deploy

See [Pipeline](/docs/pipeline) for how each stage works, or [Agents](/docs/agents) for agent-specific configuration.
