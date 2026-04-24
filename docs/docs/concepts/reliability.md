---
sidebar_position: 8
title: Reliability
---

# Reliability

Maestro is designed to run with multiple workers processing tasks concurrently. This page explains how it prevents race conditions, handles failures, and ensures durability.

## Job queue: no duplicate execution

Workers claim jobs from a PostgreSQL queue using `SELECT FOR UPDATE SKIP LOCKED`. This guarantees:

- Only one worker processes a given job
- If a worker dies mid-job, the row lock is released and another worker can claim it
- No external coordination (Redis, ZooKeeper) is needed - PostgreSQL handles it

## Comment poller: per-cycle locking

When multiple workers run simultaneously, only one should poll for new PR comments. Maestro uses a PostgreSQL transaction-level advisory lock each poll cycle:

- Each worker tries `pg_try_advisory_xact_lock(73572)` at the start of each cycle
- If acquired: this worker polls for comments, lock auto-releases when the transaction ends
- If not acquired: another worker is already polling this cycle, skip
- No persistent lock to leak - if a worker dies mid-poll, the lock is released immediately when the connection drops
- Next cycle, any worker can acquire the lock - no leader failover gap

## Duplicate dispatch prevention

Even with leader election, the comment poller has additional guards:

- **Active run check**: before dispatching, checks if there's already a running or pending agent for this task
- **Recent completion check**: if an agent finished within the last 60 seconds, skip - auto-transition is handling it
- **Status check**: only polls tasks in `in_progress` or `pending_approval` status. `failed`, `halted`, `done` are ignored

## Database connection management

- **Pool limits**: `pool_size=5, max_overflow=5` caps at 10 connections per process
- **Connection recycling**: `pool_recycle=600` refreshes connections every 10 minutes to prevent stale connections
- **Pre-ping**: `pool_pre_ping=True` tests connections before use, dropping dead ones
- **Session cleanup**: all database sessions use async context managers that guarantee cleanup on exit, even on errors

## Migration safety

When multiple processes start simultaneously (e.g., `maestro app` + `maestro worker`), both try to run database migrations. Maestro prevents deadlocks:

- Migrations are guarded by a PostgreSQL advisory lock (`pg_advisory_lock(73571)`)
- Lock is acquired and released on the same connection
- All DDL runs within a single transaction holding the lock
- If the lock can't be acquired, the process skips migrations (tables already exist)

## Auto-rebase and conflict resolution

The Implementation Agent rebases on the target branch before every pass to prevent merge conflicts from accumulating:

- **First run**: rebases before implementing
- **Follow-up runs**: rebases before addressing review comments
- Fetches the target branch name from PR/MR metadata (not hardcoded)
- If rebase produces conflicts, the agent resolves them file by file
- Force-pushes with `--force-with-lease` (safe - rejects if someone else pushed)

The Review Agent checks for merge conflicts before reviewing:

- If conflicts exist with the target branch, immediately returns REQUEST_CHANGES
- Does not review code when conflicts are present
- Posts a comment asking the Implementation Agent to rebase and resolve

## Agent identification

Each agent identifies itself in the comment footer so you can tell which agent posted what:

- `*Created by Maestro (Implementation Agent)*`
- `*Created by Maestro (Review Agent)*`
- `*Created by Maestro (Risk Profile Agent)*`

The comment poller uses this footer to detect Maestro comments and skip them when looking for new human feedback.

## Review loop

The implement/review loop has no iteration limit. Agents iterate as many times as needed until the Review Agent approves. The loop only stops when:

- Review Agent outputs REVIEW_VERDICT: APPROVE
- A user manually moves the task to `halted` or `failed`
- An agent encounters an unrecoverable error

## Agent failure handling

When an agent fails:

- The agent run is marked as `failed` with the error message
- Auto-transition checks the result and either retries or escalates

## Task halting

When a user moves a task to `halted` or `failed`:

- All running/pending agent runs for that task are killed immediately
- Agent processes receive SIGTERM for graceful shutdown
- Agent runs are marked as `failed` with "Task halted/failed by user"
- Comment poller stops checking this task
- User can resume by moving back to `in_progress`

## Worker shutdown

Workers handle graceful shutdown on SIGTERM/SIGINT:

- Stop accepting new jobs
- Drain in-flight jobs (wait for completion)
- Release the comment poller leader lock
- Deregister from the heartbeat table
- Close database connections
