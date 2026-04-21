---
sidebar_position: 3
title: Agents
---

# Agents

Agents are the AI processes that do the actual work — writing code, reviewing PRs, assessing risk, deploying, and monitoring. Each agent is a specialized subprocess that runs inside a worker.

## The five agents

| Agent | What it does | Needs LLM? |
|---|---|---|
| **Implementation** | Reads codebase, writes code, runs tests, opens a PR | Yes |
| **Review** | Posts inline comments on PRs, approves or requests changes | Yes |
| **Risk Profile** | Scores the change across 7 dimensions, auto-approves if low risk | Yes |
| **Deployment** | Verifies CI checks, merges the PR | No |
| **Monitor** | Watches metrics and logs for 15 minutes post-deploy | Yes |

## How they run

Each agent runs as a **Claude Code CLI** or **OpenAI Codex CLI** subprocess in a cloned copy of the repository. The worker manages the lifecycle — spawning, streaming output, handling timeouts, and collecting results.

Agents communicate through **PR comment threads** — the same workflow as human developers. The Implementation Agent opens a PR, the Review Agent comments on it, the Implementation Agent responds, and so on.

## Providers

Each agent can use a different LLM provider and model. Configure per-agent in the dashboard under **Agents**, or set defaults in config:

| Provider | CLI | Models |
|---|---|---|
| **Anthropic** | Claude Code CLI | Claude Sonnet, Claude Haiku |
| **OpenAI** | Codex CLI | GPT-4o, o1 |

API keys can be set globally or per-workspace in **Settings > Models**.

## Custom agents

You can add custom agents using the plugin system — linters, security scanners, notification hooks, or entirely new pipeline stages. See [Plugins](/docs/plugins) for details.
