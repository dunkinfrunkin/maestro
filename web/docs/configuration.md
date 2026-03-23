---
sidebar_position: 4
title: Configuration
---

# Configuration

Maestro is configured through the dashboard UI and environment variables.

## Environment variables

Set these in your `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://maestro:maestro@localhost:5432/maestro

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # optional, for GPT-based agents
GITHUB_TOKEN=ghp_...           # for PR creation and reviews
LINEAR_API_KEY=lin_api_...     # optional, for Linear integration

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

## Workspaces

A workspace represents a local or remote codebase that agents operate on.

**Fields:**
- **Name** — display name (e.g., "acme-api")
- **Path** — local filesystem path to the repo
- **Remote URL** — GitHub repository URL
- **Default branch** — branch to base work off (default: `main`)

Create workspaces via the dashboard under **Settings > Workspaces**.

## Projects

A project groups tasks and configuration together.

**Fields:**
- **Name** — project name
- **Workspace** — which workspace to use
- **Description** — project context for agents

## Connections

Connections configure external service integrations.

### GitHub

- **Token** — personal access token or GitHub App token
- **Owner** — repository owner (org or user)
- **Repo** — repository name

### Linear

- **API key** — Linear API key
- **Team ID** — Linear team identifier
- **Project ID** — optional Linear project to sync with

## Agent prompts

Each agent's system prompt can be customized per-project. Navigate to **Project > Settings > Agent Prompts** in the dashboard.

### Implementation agent prompt

The default prompt instructs the agent to:
- Follow existing code conventions
- Write tests for new functionality
- Keep changes focused and minimal

You can add project-specific instructions, such as:
- Preferred frameworks or libraries
- Code style requirements
- File organization patterns

### Review agent prompt

The default prompt instructs the agent to:
- Check for bugs and logic errors
- Verify input validation and error handling
- Flag performance concerns
- Suggest improvements

### Risk profile agent prompt

The default prompt instructs the agent to:
- Evaluate complexity based on diff size and logical changes
- Assess blast radius by checking dependencies
- Verify test coverage exists

## API keys

API keys for LLM providers are set as environment variables. Each agent can be configured to use a different model:

```yaml
# Example agent model configuration
agents:
  implementation:
    model: claude-sonnet-4-20250514
  review:
    model: claude-sonnet-4-20250514
  risk_profile:
    model: claude-haiku-4-20250514
  deployment:
    model: null  # no LLM needed
```
