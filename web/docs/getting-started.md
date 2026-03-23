---
sidebar_position: 1
title: Getting Started
---

# Getting Started

Get Maestro running locally in under 5 minutes.

## Prerequisites

- **Docker** and **Docker Compose** (for PostgreSQL)
- **Python 3.11+** and **uv** (for the backend)
- **Node.js 20+** and **npm** (for the frontend)
- A **Claude API key** or **Claude Code CLI** installed

## 1. Clone the repository

```bash
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro
```

## 2. Start the database

```bash
docker compose up -d
```

This starts a PostgreSQL instance on port `5432`. The default credentials are in `docker-compose.yml`.

## 3. Start the backend

```bash
cd backend
cp .env.example .env    # edit with your API keys
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

The API server starts at `http://localhost:8000`. You can verify with:

```bash
curl http://localhost:8000/health
```

## 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard opens at `http://localhost:3000`.

## 5. Create your first task

1. Open the dashboard and navigate to a project
2. Click **New Task**
3. Enter a title and description — for example:
   - Title: `Add health check endpoint`
   - Description: `Create a GET /health route that returns {"status": "ok"}`
4. Click **Queue Task**

The task enters the pipeline and flows through implementation, review, risk profiling, and deployment stages automatically.

## What happens next

- The **implementation agent** reads your codebase, writes code, and opens a pull request
- The **review agent** reads the diff and leaves inline comments
- If changes are needed, the implementation agent applies fixes and the review agent re-reviews
- The **risk profile agent** scores the change for complexity, blast radius, and test coverage
- The **deployment agent** merges the PR once everything looks good

See [Pipeline](/docs/pipeline) for a detailed breakdown of each stage.
