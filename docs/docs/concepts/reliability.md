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

## Comment poller: leader election

When multiple workers run simultaneously, only one should poll for new PR comments. Maestro uses a PostgreSQL advisory lock for leader election:

- Each worker tries to acquire `pg_try_advisory_lock(73572)` on startup
- If acquired: this worker is the leader and runs the comment poller
- If not acquired: this worker is on standby and checks again each cycle
- If the leader dies, the lock is auto-released and the next worker becomes leader

This prevents duplicate comment detection and duplicate agent dispatches.

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

## Agent failure handling

When an agent fails:

- The agent run is marked as `failed` with the error message
- Auto-transition checks the result and either retries or escalates
- Review loop has a configurable max iteration count (default: 3) to prevent infinite loops
- If max iterations are reached, the task stays in its current status for human intervention

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
