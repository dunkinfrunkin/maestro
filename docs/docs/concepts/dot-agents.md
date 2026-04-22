---
sidebar_position: 7
title: .agents/ Directory
---

# .agents/ Directory

The `.agents/` directory is a set of markdown files that live in your repository root. Agents read these files before every task to understand your codebase's architecture, conventions, security rules, and testing strategy. Think of it as a briefing packet that gives agents the context they need to write code that fits your project.

## Why it exists

LLMs can read your code, but they can't infer things like "we use Fernet for encryption" or "all API routes need auth middleware" or "never use VARCHAR, use Text." The `.agents/` directory captures the non-obvious knowledge that experienced developers carry in their heads.

## How to create it

```bash
maestro repo init
```

This scaffolds 11 template files in `.agents/`. Each file has placeholder comments (`<!-- FILL: ... -->`) that you replace with real information about your codebase.

## The files

| File | What it contains | Which agents read it |
|---|---|---|
| **SPECIFICATION.md** | Problem statement, acceptance criteria, risks | Planner, Implementer, Reviewer, QA |
| **ARCHITECTURE.md** | System overview, service boundaries, data flow | Planner, Implementer, Reviewer, Risk |
| **DATABASE.md** | Schema, migrations, indexes, conventions | Planner, Implementer, Risk |
| **API_CONTRACTS.md** | Endpoints, request/response shapes, error codes | Planner, QA |
| **STYLE_GUIDE.md** | Code conventions, naming, formatting, patterns | Implementer, Reviewer |
| **SECURITY.md** | Auth, secrets, input validation, OWASP checklist | Implementer, Reviewer, Risk |
| **COMPLIANCE.md** | Regulatory requirements, PII handling, audit rules | Implementer, Reviewer, Risk |
| **TEST_STRATEGY.md** | Testing philosophy, coverage targets, fixtures | QA |
| **RUNBOOK.md** | Health checks, incident response, rollback | Risk, Deploy, Monitor |
| **DEPLOY.md** | Environments, CI/CD pipeline, feature flags | Deploy |
| **MONITORING.md** | Key metrics, SLOs, dashboards, alerting | Monitor |

## What to put in them

Be specific. Reference actual file paths, function names, table names, and conventions found in your code.

**Good:**
- "All API routes are in `engine/maestro/api/` and use FastAPI routers"
- "Authentication uses JWT in HTTP-only cookies, implemented in `auth.py`"
- "Database migrations use Alembic, run with `alembic upgrade head`"

**Bad:**
- "We use a modern web framework" (agents can see this from the code)
- "Follow best practices" (too vague to be actionable)
- "We should eventually add more tests" (aspirational, not current state)

## When to update

Update `.agents/` files when your codebase changes significantly - new services, changed conventions, different auth patterns, new infrastructure. Stale context is worse than no context because it leads agents to make wrong assumptions.

## Example

A minimal `ARCHITECTURE.md` for a FastAPI + Next.js project:

```markdown
# Architecture

## Overview
Maestro is a monorepo with a Python FastAPI backend and Next.js frontend.

## Directory Structure
- `engine/` - FastAPI server, SQLAlchemy models, agent implementations
- `ui/` - Next.js 16 App Router, Tailwind CSS
- `cli/` - Go CLI distributed via Homebrew

## Data Flow
1. Frontend calls `/api/v1/*` endpoints
2. FastAPI handles auth, validates input, queries PostgreSQL
3. Agent jobs are dispatched via a PostgreSQL queue
4. Workers pick up jobs and run Claude Code or Codex CLI

## Key Decisions
- Async everywhere (asyncpg, async SQLAlchemy)
- JWT auth in HTTP-only cookies, OIDC/SSO for enterprise
- Fernet encryption for stored tokens
```
