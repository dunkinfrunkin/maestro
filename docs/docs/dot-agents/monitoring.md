---
sidebar_position: 11
title: MONITORING.md
---

# MONITORING.md

**Read by:** Monitor

## Why it exists

The Monitor Agent watches your system for 15 minutes after every deploy. It needs to know what "normal" looks like: baseline metrics, alert thresholds, which dashboards to check, and what constitutes an anomaly worth flagging. Without this context, the agent either misses real problems or cries wolf on normal variance.

## What to include

- **Key metrics** - What to measure, baseline values, alert thresholds
- **SLOs** - Service level objectives the team has committed to
- **Dashboards** - Where to find observability data
- **Alerting** - How alerts work and who gets paged
- **Post-deploy monitoring** - Specifically what to watch after a deploy

## Example

```markdown
# Monitoring

## Key Metrics
| Metric | Baseline | Alert threshold |
|---|---|---|
| API p99 latency | 200ms | > 500ms |
| Error rate (5xx) | < 0.1% | > 1% |
| Agent success rate | > 90% | < 70% |
| DB connection pool | < 50% utilized | > 80% |

## SLOs
- 99.9% uptime (measured monthly)
- API p95 < 300ms
- Agent completion within 30 minutes

## Post-Deploy Monitoring
After every deploy, watch for 15 minutes:
1. Error rate spike (compare to 1-hour pre-deploy baseline)
2. Latency increase (p99 > 2x baseline)
3. New exception patterns in logs
4. Memory/CPU spike on API or worker processes

If any threshold is breached, flag the task and alert the team.
```
