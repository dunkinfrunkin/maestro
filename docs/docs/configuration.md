---
sidebar_position: 7
title: Configuration
---

# Configuration

Maestro is configured through environment variables and the dashboard UI.

## Environment variables

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://maestro:maestro@localhost:5432/maestro

# LLM provider (required - at least one)
ANTHROPIC_API_KEY=sk-ant-...

# Tracker integrations (optional)
GITHUB_TOKEN=ghp_...
LINEAR_API_KEY=lin_api_...

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

All tokens are encrypted at rest using Fernet symmetric encryption before being stored in the database.

## Workspaces

A workspace represents a codebase that agents operate on.

| Field | Description |
|---|---|
| Name | Display name (e.g., `acme-api`) |
| Path | Local filesystem path to the repo |
| Remote URL | GitHub repository URL |
| Default branch | Branch to base work off (default: `main`) |

Create and manage workspaces via **Settings > Workspaces** in the dashboard.

## Projects

A project groups tasks, agent configurations, and pipeline settings together.

| Field | Description |
|---|---|
| Name | Project display name |
| Workspace | Which workspace to use |
| Description | Context for agents (helps them understand the codebase) |

Each project has its own agent prompts, risk thresholds, and connection settings.

## Connections

### GitHub

| Field | Description |
|---|---|
| Token | Personal access token or GitHub App token |
| Owner | Repository owner (org or user) |
| Repo | Repository name (or `*` for all repos) |

### Linear

| Field | Description |
|---|---|
| API key | Linear API key |
| Team ID | Linear team identifier |
| Project ID | Optional - sync a specific Linear project |

## Agent prompts

Each agent's system prompt can be customized per-project from the dashboard under **Agents**.

The prompt editor uses CodeMirror with markdown syntax highlighting. Changes are saved immediately and apply to the next agent run.

**What you can customize:**
- Code style and conventions for the Implementation Agent
- Review criteria and severity rules for the Review Agent
- Risk dimension weights for the Risk Profile Agent
- Monitoring thresholds for the Monitor Agent

## Model selection

Each agent can use a different model. Configure per-agent in the dashboard or via the API:

| Agent | Default model | Notes |
|---|---|---|
| Implementation | `claude-sonnet-4-6` | Needs strong coding ability |
| Review | `claude-sonnet-4-6` | Needs to reason about code quality |
| Risk Profile | `claude-haiku-4-5` | Lighter task, faster model works well |
| Deployment | None | No LLM needed - uses `gh` CLI directly |
| Monitor | `claude-haiku-4-5` | Reads logs and metrics |
