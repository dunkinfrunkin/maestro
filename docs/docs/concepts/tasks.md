---
sidebar_position: 4
title: Tasks
---

# Tasks

A task is a unit of work that flows through the Maestro pipeline. Tasks originate from your issue tracker and represent a single change to implement.

## Lifecycle

1. An issue is created in your tracker (GitHub Issues, Linear, Jira, GitLab)
2. Maestro syncs it and it appears on the **Tasks** page
3. You assign a repository and move it to **Implement**
4. The pipeline takes over — implement → review → risk → deploy → monitor
5. The task reaches **Done** or **Failed**

## Pipeline states

| State | What's happening |
|---|---|
| **Queued** | Task is synced, waiting to be assigned and started |
| **Implement** | Implementation Agent is writing code and opening a PR |
| **Review** | Review Agent is posting inline comments |
| **Risk Profile** | Risk Agent is scoring the change |
| **Deploy** | Deploy Agent is verifying CI and merging |
| **Monitor** | Monitor Agent is watching for regressions |
| **Done** | Successfully completed |
| **Failed** | Unrecoverable error at any stage |
| **Blocked** | Needs human intervention (high-risk PR, CI failure) |

## Task detail

Each task has a detail page showing:

- Current pipeline state and progress
- Linked PR/MR with status
- Agent run history with token usage and logs
- Execution trace timeline
- Activity feed with all state transitions
