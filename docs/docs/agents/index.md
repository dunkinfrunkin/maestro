---
sidebar_position: 4
title: Agents
sidebar_label: Agents
---

# Agents

Agents are the AI processes that do the actual work in Maestro. Each agent is a specialized subprocess that runs inside a worker, operating on a cloned copy of your repository. Agents communicate through PR comment threads - the same workflow as human developers.

Every agent runs as a Claude Code CLI or OpenAI Codex CLI process with access to Read, Write, Edit, Bash, Glob, and Grep tools.

| Agent | Lifecycle stage | What it does | Needs LLM? |
|---|---|---|---|
| **Implementation** | implementing | Writes code, runs tests, opens PR | Yes |
| **Review** | in-review | Posts inline comments, approves or requests changes | Yes |
| **Risk Profile** | in-review | Scores change across 7 dimensions | Yes |
| **Deployment** | deploying | Verifies CI, merges PR, deploys | No |
| **Monitor** | deploying | Watches metrics and logs post-deploy | Yes |

## Providers

Each agent can use a different LLM provider and model. Configure per-agent in the dashboard under **Agents**, or set defaults per-workspace.

| Provider | CLI tool | Models |
|---|---|---|
| **Anthropic** | Claude Code CLI | Claude Sonnet, Claude Haiku |
| **OpenAI** | Codex CLI | GPT-4o, o1 |

API keys can be set globally or per-workspace in **Settings > Models**.

