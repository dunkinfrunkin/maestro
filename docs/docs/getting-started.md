---
sidebar_position: 1
title: Getting Started
---

# Getting Started

Get Maestro running in under 5 minutes.

## Install

```bash
brew install dunkinfrunkin/tap/maestro
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

Start the app and worker in two terminals:

```bash
# Terminal 1 - dashboard + API
maestro app
```

```bash
# Terminal 2 - agent worker (processes tasks)
maestro worker
```

Dashboard opens at [localhost:3000](http://localhost:3000). The worker picks up tasks and runs agents.

## Connect your integrations

Maestro needs two things to work: a **codebase** (where agents write code) and a **tracker** (where tasks come from).

Open the dashboard at [localhost:3000](http://localhost:3000) and go to **Settings > Connections**.

### Option A: GitHub for both

GitHub serves as both codebase and tracker - agents open PRs and pull tasks from GitHub Issues.

1. Add a **GitHub** connection with a personal access token or GitHub App
2. Select the repositories you want Maestro to work on

### Option B: Separate codebase + tracker

Use GitHub or GitLab as the codebase, and Jira or Linear as the tracker.

1. Add a **GitHub** or **GitLab** connection for your codebase
2. Add a **Jira** or **Linear** connection for your issue tracker
3. Link them to the same workspace

| Integration | Role | What Maestro does with it |
|---|---|---|
| **GitHub** | Codebase + Tracker | Opens PRs, posts reviews, reads issues |
| **GitLab** | Codebase + Tracker | Opens MRs, posts discussions, reads issues |
| **Linear** | Tracker only | Syncs issues, updates status |
| **Jira** | Tracker only | Syncs issues, updates status |

Once connected, Maestro automatically syncs issues and you can queue tasks from the dashboard.

## Run your first task

1. Create an issue in your tracker (GitHub Issues, Linear, Jira, or GitLab)
2. The issue syncs automatically and appears in the Maestro **Tasks** page
3. Assign a repository to the task
4. Move the task to **Implement** to kick off the pipeline

Once in Implement, five agents take over in sequence:

1. **Implementation** - reads your codebase, writes code, runs tests, opens a PR
2. **Review** - posts inline comments on specific lines, requests changes or approves
3. **Risk Profile** - scores the PR across seven dimensions, auto-approves if low risk
4. **Deployment** - verifies CI checks, merges via squash
5. **Monitor** - watches metrics and logs for 15 minutes post-deploy

You can watch each stage in real time from the task detail page.

See [Pipeline](/docs/pipeline) for how each stage works, or [Agents](/docs/agents) for agent-specific configuration.

## CLI commands

| Command | What it does |
|---|---|
| `maestro app` | Start full stack (backend + frontend) |
| `maestro serve` | Start API server only |
| `maestro worker` | Start agent worker process |
| `maestro init` | Generate `~/.maestro/config.yaml` |
| `maestro repo init` | Scaffold `.agents/` templates for a repo |
