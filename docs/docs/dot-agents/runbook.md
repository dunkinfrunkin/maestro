---
sidebar_position: 9
title: RUNBOOK.md
---

# RUNBOOK.md

**Read by:** Risk, Deploy, Monitor

## Why it exists

The Risk Profile Agent needs to know what "reversible" means for your system. The Deploy Agent needs to know the rollback procedure. The Monitor Agent needs to know what a healthy system looks like. Without operational context, these agents can't make good judgments about whether a change is safe to ship.

## What to include

- **Health checks** - How to verify the system is healthy
- **Common issues** - Known failure modes and their fixes
- **Incident response** - Step-by-step procedure when things break
- **Escalation** - Who to contact and when
- **Rollback procedure** - How to undo a bad deploy

## Example

```markdown
# Runbook

## Health Checks
- GET / returns {"status": "ok"}
- PostgreSQL: pg_isready -U maestro
- Frontend: curl http://localhost:3000

## Common Issues
| Symptom | Likely Cause | Fix |
|---|---|---|
| 503 on /api/v1/state | Orchestrator not started | Check DB connection |
| Agent timeout | LLM rate limited | Wait and retry |
| PR creation fails | Token expired | Refresh in Settings > Connections |

## Rollback Procedure
1. Identify the bad commit via git log
2. git revert <commit> and push
3. Verify health checks pass
4. Monitor for 15 minutes post-rollback
```
