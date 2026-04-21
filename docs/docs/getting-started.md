---
sidebar_position: 1
title: Getting Started
---

# Getting Started

Get Maestro running in under 5 minutes.

## Install

### Homebrew (macOS / Linux)

```bash
brew install dunkinfrunkin/tap/maestro
```

### From source

```bash
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro
make install
```

## Configure

Generate a default config file:

```bash
maestro init
```

This creates `~/.maestro/config.yaml`. Edit it with your database URL and API keys:

```yaml
database:
  url: postgresql+asyncpg://maestro:maestro@localhost:5432/maestro

anthropic:
  api_key: sk-ant-...
```

See [Configuration](/docs/configuration) for all options.

## Start

### With Homebrew (Docker-based)

```bash
maestro app
```

This pulls the Docker image and starts the full stack — backend, frontend, and nginx — on port 3000.

### From source (local development)

```bash
# Start PostgreSQL
make db

# Start backend + frontend
maestro app
```

Dashboard opens at [localhost:3000](http://localhost:3000).

## Create your first task

1. Open the dashboard at [localhost:3000](http://localhost:3000)
2. Go to **Settings > Connections** and add your GitHub or GitLab connection
3. Select a repository and click **New Task**
4. Enter a title and description — for example:
   - **Title:** `Add health check endpoint`
   - **Description:** `Create a GET /health route that returns {"status": "ok"}`
5. Click **Queue Task**

The task enters the pipeline and flows through each stage automatically. Watch it happen in real time from the task detail page.

## What happens next

Once queued, five agents take over in sequence:

1. **Implementation** — reads your codebase, writes code, runs tests, opens a PR
2. **Review** — posts inline comments on specific lines, requests changes or approves
3. **Risk Profile** — scores the PR across seven dimensions, auto-approves if low risk
4. **Deployment** — verifies CI checks, merges via squash
5. **Monitor** — watches metrics and logs for 15 minutes post-deploy

See [Pipeline](/docs/pipeline) for how each stage works, or [Agents](/docs/agents) for agent-specific configuration.

## CLI commands

| Command | What it does |
|---|---|
| `maestro app` | Start full stack (backend + frontend) |
| `maestro serve` | Start API server only |
| `maestro worker` | Start agent worker process |
| `maestro init` | Generate `~/.maestro/config.yaml` |
| `maestro repo init` | Scaffold `.agents/` templates for a repo |
