---
sidebar_position: 2
title: Workers
---

# Workers

Workers are the processes that actually run agents. They pick up jobs dispatched by CENTCOM and execute them.

## What they do

- Poll the PostgreSQL job queue for dispatched tasks (`SELECT FOR UPDATE SKIP LOCKED`)
- Run agent processes (Claude Code CLI or OpenAI Codex CLI) in cloned repo workspaces
- Report results back - token usage, success/failure, logs
- Send heartbeats so CENTCOM knows they're alive
- Poll open PRs for new human comments and re-dispatch agents to address them

## How to run

```bash
maestro worker                  # default: 3 concurrent jobs
maestro worker --concurrency 5  # run up to 5 agents at once
```

## Deployment options

Workers can run anywhere that has Docker (for the agent CLIs) and network access to PostgreSQL and your code hosts.

| Setup | How | Best for |
|---|---|---|
| **Same machine** | Run `maestro worker` alongside `maestro app` | Local dev, small teams |
| **Separate container** | Docker Compose with `worker` service | Staging, production |
| **Horizontal scale** | Multiple `worker` replicas sharing the same DB | High throughput |
| **Cloud VMs** | Workers on dedicated VMs close to your code host | Large repos, low latency |

Workers are stateless - you can scale them up/down or restart them without losing work. In-flight jobs are gracefully drained on shutdown.

## Concurrency

Each worker runs up to N agents in parallel (default: 3). Total system concurrency = number of workers × concurrency per worker.

Configure via CLI flag, config.yaml, or environment:

```bash
maestro worker --concurrency 5
```

```yaml
# ~/.maestro/config.yaml
worker:
  concurrency: 5
  poll_interval: 2.0
  comment_poll_interval: 60.0
```

## Comment polling

Each worker runs a background loop that checks open PRs for new human comments. When someone posts a review comment on a PR outside of Maestro, the worker detects it and automatically dispatches the Implementation Agent to address it.

- Polls every 60 seconds by default (configurable)
- Only checks tasks in "in_progress" or "pending_approval" status with an open PR
- Filters out comments made by Maestro agents (only human comments trigger re-dispatch)
- Moves the task back to "in_progress" and runs the agent to address the feedback

```bash
maestro worker --comment-poll-interval 30   # check every 30s
maestro worker --comment-poll-interval 0    # disable comment polling
```
