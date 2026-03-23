---
sidebar_position: 2
title: Pipeline
---

# The Harness Engineering Pipeline

Every task in Maestro flows through a deterministic pipeline. Each stage is handled by a specialized agent, and the pipeline enforces quality gates between stages.

## Pipeline stages

### Queued

A task enters the queue when it's created — either manually from the dashboard, via the API, or synced from a GitHub issue or Linear ticket.

**What happens:**
- Task is validated and assigned to a workspace
- The task receives a unique internal ID
- Status is set to `queued`

### Implement

The implementation agent picks up the task and writes code.

**What happens:**
- Agent reads the project codebase to understand context
- Writes the implementation based on the task description
- Creates a Git branch and opens a pull request
- Attaches the PR link to the task

### Review

The review agent reads the pull request diff and performs an inline code review.

**What happens:**
- Agent reads the full diff of the PR
- Leaves inline comments on specific lines where it finds issues
- Comments cover: bugs, missing validation, style, performance, security
- If no issues are found, the review is approved immediately

### Review loop

If the review agent leaves comments, the task cycles back to the implementation agent:

1. Implementation agent reads the review comments
2. Applies fixes and pushes new commits
3. Task returns to the review agent for re-review
4. This loop continues until all comments are resolved

The loop has a configurable maximum iteration count (default: 5) to prevent infinite cycles.

### Risk Profile

After the review is approved, the risk profile agent analyzes the change.

**What happens:**
- Scores the change across multiple dimensions:
  - **Complexity** — how many files, lines, and logical branches are affected
  - **Blast radius** — how many other modules depend on the changed code
  - **Test coverage** — whether tests exist for the new/changed code
- Produces an overall risk score: `LOW`, `MEDIUM`, or `HIGH`
- `LOW` tasks can be auto-merged; `HIGH` tasks require human approval

### Deploy

The deployment agent handles merging and CI.

**What happens:**
- Merges the PR into the target branch
- Monitors CI pipeline status
- Reports success or failure back to the task

### Monitor

Post-deployment monitoring (when configured).

**What happens:**
- Watches application logs and metrics for anomalies
- If errors spike after deployment, the task is flagged for rollback review
- Reports monitoring status back to the task

## Status transitions

```
queued → implement → review ↔ implement (loop) → risk_profile → deploy → monitor → done
```

At any point, a task can transition to `failed` if an unrecoverable error occurs, or `blocked` if human intervention is required.
