---
sidebar_position: 1
title: CENTCOM
---

# CENTCOM

CENTCOM is the central command server - the brain of Maestro. It runs the API, the dashboard, and the orchestrator that coordinates everything.

## What it does

- Serves the **REST API** and **dashboard UI**
- Runs the **orchestrator** - polls trackers for new issues, manages pipeline state, dispatches work to workers
- Handles **authentication** (OIDC/SSO) and **connection management** (encrypted token storage)
- Stores all state in **PostgreSQL** - tasks, pipeline records, agent runs, connections, workspaces

## How it runs

CENTCOM is what starts when you run:

```bash
maestro app     # full stack: API + frontend + nginx
maestro serve   # API server only (no frontend)
```

In production, CENTCOM runs as a single container with nginx reverse-proxying the API (port 8000) and frontend (port 3001) behind a single port (3000).

## Orchestrator

The orchestrator is the engine inside CENTCOM that drives the pipeline:

1. **Polls** connected trackers for issues on a configurable interval
2. **Reconciles** running agents - detects stalls, checks if issues moved to terminal states
3. **Dispatches** eligible tasks to available workers based on priority and concurrency limits
4. **Retries** failed tasks with exponential backoff

The orchestrator is stateless across restarts - all durable state lives in PostgreSQL.
