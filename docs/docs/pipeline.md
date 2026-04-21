---
sidebar_position: 2
title: Pipeline
---

# Pipeline

Every task in Maestro flows through a deterministic pipeline. Each stage is handled by a specialized agent, and the pipeline enforces quality gates between them.

```
Queued → Implement → Review ↔ Implement → Risk Profile → Deploy → Monitor → Done
```

## Queued

A task enters the queue when created from the dashboard, via the API, or synced from GitHub/Linear.

- Task is validated and assigned to a workspace
- Receives a unique internal ID
- Status set to `queued`

## Implement

The Implementation Agent picks up the task and writes code.

- Reads the project codebase to understand context and conventions
- Writes the implementation based on the task description
- Runs the test suite to verify correctness
- Creates a Git branch and opens a pull request
- Attaches the PR link to the task

## Review

The Review Agent reads the pull request and performs inline code review.

- Checks out the PR and reads every changed file
- Posts inline comments on specific lines where issues are found
- Comments cover bugs, missing validation, style, performance, and security
- If no issues are found, approves immediately

## Review loop

If the Review Agent requests changes, the task cycles back to the Implementation Agent:

1. Implementation Agent reads the review comments
2. Applies fixes and pushes new commits
3. Replies directly in the PR comment thread
4. Review Agent re-reviews and verifies each fix
5. Resolves threads and approves once everything is addressed

The loop has a configurable maximum iteration count (default: 5) to prevent infinite cycles.

## Risk Profile

After review approval, the Risk Profile Agent scores the change.

| Dimension | What it measures |
|---|---|
| Scope | Files and lines changed |
| Blast radius | Systems and users affected |
| Complexity | Cyclomatic complexity, new abstractions |
| Test coverage | Whether tests exist for changed paths |
| Security | Auth, crypto, PII, secrets handling |
| Reversibility | Can this be rolled back cleanly? |
| Dependencies | New or updated external packages |

Each dimension is scored 1-5. The overall risk level is `LOW`, `MEDIUM`, or `HIGH`.

- **LOW** — auto-approved for merge
- **MEDIUM** — requires one human approval
- **HIGH** — requires explicit human sign-off

The auto-approve threshold is configurable per workspace.

## Deploy

The Deployment Agent handles merging and CI verification.

- Checks all GitHub Actions pipelines (build, lint, test, deploy-preview)
- Waits for all checks to pass
- Merges the PR via squash into the target branch
- Reports success or failure back to the task

## Monitor

The Monitor Agent watches for post-deploy regressions.

- Checks Datadog dashboards for latency and error rate changes
- Queries Splunk logs for new exceptions
- Monitors for 15 minutes after deploy
- Flags the change if anomalies are detected

## Status transitions

At any point, a task can transition to:

- **failed** — unrecoverable error during any stage
- **blocked** — human intervention required (high-risk PR, CI failure, etc.)

All transitions are logged in the task activity feed and visible in the dashboard.
