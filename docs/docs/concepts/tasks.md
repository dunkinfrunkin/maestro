---
sidebar_position: 4
title: Tasks
---

# Tasks

A task is a unit of work that flows through the Maestro pipeline. Tasks originate from your issue tracker and represent a single change to implement.

## Lifecycle

1. An issue is created in your tracker (GitHub Issues, Linear, Jira, GitLab)
2. Maestro syncs it and it appears on the **Tasks** page
3. You assign a repository and move it to **In Progress**
4. The pipeline takes over - in_progress → pending_approval → approved → deploy
5. The task reaches **Done** or **Failed**

## Pipeline states

| State | What's happening |
|---|---|
| **todo** | Task is synced, waiting for user to trigger |
| **in_progress** | Agentic loop: implement, AI review, AI risk profile |
| **pending_approval** | AI work done, waiting for human review and approval |
| **approved** | Human approved, auto-merge and deploy to lower envs (not yet implemented) |
| **promote** | Lower envs healthy, promoting to production (not yet implemented) |
| **deploy** | Deploying to prod, monitoring (not yet implemented) |
| **done** | Successfully completed |
| **failed** | Error at any stage |
| **halted** | User manually stopped |

## Task detail

Each task has a detail page showing:

- Current pipeline state and progress
- Linked PR/MR with status
- Agent run history with token usage and logs
- Execution trace timeline
- Activity feed with all state transitions
