---
sidebar_position: 5
title: Monitor
---

# Monitor Agent

The Monitor Agent watches for post-deploy regressions in production. It runs for a configurable window (default: 15 minutes) after deployment and flags the task if anomalies are detected.

## What it does

1. Queries metrics dashboards for latency (p99) and error rate changes
2. Checks logs for new exceptions or error patterns
3. Compares current metrics against pre-deploy baseline
4. Monitors for the configured window (default: 15 minutes)
5. If anomalies are detected, flags the task and can trigger a rollback
6. If the window passes clean, marks the task as **done**

## Inputs

- Deployment timestamp
- Pre-deploy baseline metrics
- Metrics and logging endpoints (configured per workspace)

## Outputs

- Monitoring report (metrics comparison)
- Pass/fail verdict
- Alert if anomalies detected
- Task status update to **done** or **failed**

## Configuration

| Setting | Default | Description |
|---|---|---|
| model | `claude-haiku-4-5` | LLM model for log analysis |
| provider | `anthropic` | `anthropic` or `openai` |
| monitoring_window | `15m` | Duration to watch after deploy |
| error_threshold | `50%` | Error rate increase that triggers alert |
| log_sources | `datadog,splunk` | Which monitoring systems to query |
| enabled | `true` | Enable or disable this agent |

Configure per-workspace in the dashboard under **Agents > Monitor**.
