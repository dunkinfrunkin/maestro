---
sidebar_position: 2
title: ARCHITECTURE.md
---

# ARCHITECTURE.md

**Read by:** Planner, Implementer, Reviewer, Risk

## Why it exists

An agent can explore your directory structure, but it can't infer why things are organized the way they are. It doesn't know that `engine/maestro/external/` is for third-party integrations or that `ui/src/lib/api.ts` is the single source of truth for all API calls. Without architectural context, agents put code in the wrong place, duplicate existing patterns, or break boundaries between modules.

This file gives agents a map of the system before they start working.

## What to include

- **Overview** - One paragraph describing what the application does
- **Directory structure** - What each top-level directory contains and why
- **Service boundaries** - What talks to what, and through which interfaces
- **Data flow** - Trace a typical request through the system, naming actual files
- **External dependencies** - Systems the app depends on and what happens when they fail
- **Key design decisions** - Architectural choices and WHY they were made

## Example

```markdown
# Architecture

## Overview
Maestro is a monorepo with a Python FastAPI backend, Next.js frontend,
and Go CLI. The backend manages the agent orchestration pipeline, the
frontend provides the dashboard UI, and the CLI is the distribution
mechanism for end users.

## Directory Structure
- engine/maestro/api/ - FastAPI routers, one file per resource
- engine/maestro/agent/ - Agent implementations (one per pipeline stage)
- engine/maestro/db/ - SQLAlchemy models and CRUD operations
- engine/maestro/external/ - Third-party integrations (GitHub, GitLab, Linear, Jira)
- ui/src/app/ - Next.js App Router pages
- ui/src/lib/api.ts - All API calls go through authFetch()

## Data Flow
1. Frontend calls /api/v1/* via authFetch() with JWT bearer token
2. FastAPI validates the token, runs the handler, queries PostgreSQL
3. For agent work: orchestrator dispatches a job to the PostgreSQL queue
4. A worker picks up the job (SELECT FOR UPDATE SKIP LOCKED)
5. Worker runs Claude Code or Codex CLI in a cloned repo workspace
6. Agent opens a PR via the code host API

## Key Decisions
- Async everywhere: asyncpg, async SQLAlchemy, asyncio workers
- PostgreSQL as the job queue (no Redis/RabbitMQ dependency)
- JWT in HTTP-only cookies for auth, OIDC/SSO for enterprise
- Fernet encryption for stored integration tokens
```
