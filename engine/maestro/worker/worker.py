"""Worker process — claims and executes agent jobs from the PostgreSQL queue."""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import signal
import sys
import uuid
from datetime import datetime, timezone

from maestro.db.engine import get_session, init_db
from maestro.db.models import AgentRun, AgentRunStatus, ApiKeyProvider, WorkerHeartbeat
from maestro.db import crud
from maestro.agents.plugin import registry, init_plugins

logger = logging.getLogger(__name__)


async def claim_next_job() -> AgentRun | None:
    """Claim the next PENDING job using SELECT FOR UPDATE SKIP LOCKED."""
    from sqlalchemy import select, text

    async with get_session() as session:
        # Atomic claim: select + update in one transaction
        result = await session.execute(
            select(AgentRun)
            .where(AgentRun.status == AgentRunStatus.PENDING)
            .order_by(AgentRun.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        run = result.scalar_one_or_none()
        if not run:
            return None

        # Mark as claimed — don't set RUNNING yet, _execute_agent does that
        # But we need to return the object detached from session
        run_id = run.id
        workspace_id = run.workspace_id
        task_pipeline_id = run.task_pipeline_id
        agent_type = run.agent_type
        model = run.model
        job_payload = run.job_payload
        triggered_by = run.triggered_by

    # Return a fresh object with the data we need
    return type("ClaimedJob", (), {
        "id": run_id,
        "workspace_id": workspace_id,
        "task_pipeline_id": task_pipeline_id,
        "agent_type": agent_type,
        "model": model,
        "job_payload": job_payload,
        "triggered_by": triggered_by,
    })()


async def execute_job(job) -> None:
    """Execute a claimed agent job."""
    from maestro.worker.dispatcher import _execute_agent
    from maestro.db.encryption import decrypt_token

    run_id = job.id
    payload = json.loads(job.job_payload) if job.job_payload else {}

    if not payload or not payload.get("plugin_name"):
        logger.error("Run %d has empty job_payload, marking as failed", run_id)
        async with get_session() as session:
            from datetime import datetime, timezone
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.FAILED
                run.error = "Empty job payload"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        return

    # Resolve plugin
    plugin_name = payload["plugin_name"]
    plugin = registry.get(plugin_name)
    if not plugin:
        logger.error("Run %d: unknown plugin '%s'", run_id, plugin_name)
        async with get_session() as session:
            from datetime import datetime, timezone
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.FAILED
                run.error = f"Unknown plugin: {plugin_name}"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        return

    # Decrypt API key
    provider = payload.get("provider", "anthropic")
    try:
        provider_enum = ApiKeyProvider(provider)
    except ValueError:
        provider_enum = ApiKeyProvider.ANTHROPIC

    async with get_session() as session:
        api_key_record = await crud.get_api_key(session, job.workspace_id, provider_enum)

    if not api_key_record:
        logger.error("Run %d: no %s API key for workspace %d", run_id, provider, job.workspace_id)
        async with get_session() as session:
            from datetime import datetime, timezone
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.FAILED
                run.error = f"No {provider} API key configured"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        return

    api_key = decrypt_token(api_key_record.encrypted_key)

    print(f"[WORKER] Executing run {run_id} ({plugin_name}, {payload.get('model', 'sonnet')})")

    await _execute_agent(
        run_id=run_id,
        plugin=plugin,
        api_key=api_key,
        provider=provider,
        model=payload.get("model", "sonnet"),
        workspace_id=job.workspace_id,
        task_pipeline_id=job.task_pipeline_id,
        issue_title=payload.get("issue_title", ""),
        issue_description=payload.get("issue_description", ""),
        issue_url=payload.get("issue_url", ""),
        pr_url=payload.get("pr_url", ""),
        pr_number=payload.get("pr_number", ""),
        repo=payload.get("repo", ""),
        clone_url=payload.get("clone_url", ""),
        code_host=payload.get("code_host", ""),
        extra_config=payload.get("extra_config", {}),
    )

    print(f"[WORKER] Run {run_id} finished")


async def _register_worker(worker_id: str, concurrency: int) -> None:
    """Register this worker in the DB."""
    sys_metrics = _get_system_metrics()
    async with get_session() as session:
        hb = WorkerHeartbeat(
            id=worker_id,
            hostname=platform.node(),
            concurrency=concurrency,
            active_jobs=0,
            status="online",
            last_heartbeat=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            **sys_metrics,
        )
        session.add(hb)
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            await session.execute(
                WorkerHeartbeat.__table__.update()
                .where(WorkerHeartbeat.id == worker_id)
                .values(
                    status="online",
                    hostname=platform.node(),
                    concurrency=concurrency,
                    active_jobs=0,
                    last_heartbeat=datetime.now(timezone.utc),
                    started_at=datetime.now(timezone.utc),
                    **sys_metrics,
                )
            )
            await session.commit()


def _get_system_metrics() -> dict:
    """Collect system CPU, memory, and estimate agent capacity."""
    import psutil

    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    memory_used_mb = (mem.total - mem.available) / (1024 * 1024)
    memory_total_mb = mem.total / (1024 * 1024)
    cpu_count = psutil.cpu_count() or 1

    # Estimate capacity: each agent uses ~300MB RAM and ~1 CPU core
    # Available = what's free, not what's total
    available_mem_mb = mem.available / (1024 * 1024)
    mem_slots = int(available_mem_mb / 300)  # ~300MB per agent (CLI + subprocess)
    cpu_slots = max(1, int(cpu_count * (100 - cpu_percent) / 100))  # free CPU cores
    estimated_capacity = max(0, min(mem_slots, cpu_slots))

    return {
        "cpu_percent": round(cpu_percent, 1),
        "memory_used_mb": round(memory_used_mb, 0),
        "memory_total_mb": round(memory_total_mb, 0),
        "cpu_count": cpu_count,
        "estimated_capacity": estimated_capacity,
    }


async def _send_heartbeat(worker_id: str, active_jobs: int) -> None:
    """Update heartbeat with system metrics."""
    try:
        sys_metrics = _get_system_metrics()
        async with get_session() as session:
            await session.execute(
                WorkerHeartbeat.__table__.update()
                .where(WorkerHeartbeat.id == worker_id)
                .values(
                    last_heartbeat=datetime.now(timezone.utc),
                    active_jobs=active_jobs,
                    **sys_metrics,
                )
            )
            await session.commit()
    except Exception:
        pass  # Non-fatal


async def _deregister_worker(worker_id: str) -> None:
    """Mark worker as offline."""
    try:
        async with get_session() as session:
            await session.execute(
                WorkerHeartbeat.__table__.update()
                .where(WorkerHeartbeat.id == worker_id)
                .values(status="offline", active_jobs=0)
            )
            await session.commit()
    except Exception:
        pass


async def run_worker(
    concurrency: int = 3,
    poll_interval: float = 2.0,
    comment_poll_interval: float = 60.0,
) -> None:
    """Main worker loop - claims and executes agent jobs."""
    await init_db()
    init_plugins()

    worker_id = str(uuid.uuid4())[:12]
    await _register_worker(worker_id, concurrency)

    semaphore = asyncio.Semaphore(concurrency)
    active_tasks: set[asyncio.Task] = set()
    shutdown = asyncio.Event()

    def handle_signal():
        print("[WORKER] Shutdown signal received, draining...")
        shutdown.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    print(f"[WORKER] {worker_id} started on {platform.node()} (concurrency={concurrency})")

    # Heartbeat background task
    async def heartbeat_loop():
        while not shutdown.is_set():
            active = concurrency - semaphore._value
            await _send_heartbeat(worker_id, active)
            try:
                await asyncio.wait_for(shutdown.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass

    hb_task = asyncio.create_task(heartbeat_loop())

    # Comment poller background task (leader-elected via advisory lock)
    comment_task = None
    if comment_poll_interval > 0:
        from maestro.worker.comment_poller import run_comment_poller
        comment_task = asyncio.create_task(
            run_comment_poller(interval=comment_poll_interval, shutdown=shutdown)
        )

    while not shutdown.is_set():
        # Clean up finished tasks
        done = {t for t in active_tasks if t.done()}
        for t in done:
            try:
                t.result()
            except Exception as e:
                logger.exception("Worker task failed: %s", e)
        active_tasks -= done

        # Try to claim a job if we have capacity
        if semaphore._value > 0:
            try:
                job = await claim_next_job()
            except Exception as e:
                logger.exception("Failed to claim job: %s", e)
                job = None

            if job:
                async def run_with_semaphore(j):
                    async with semaphore:
                        await execute_job(j)

                task = asyncio.create_task(run_with_semaphore(job))
                active_tasks.add(task)
                continue

        # No job or at capacity — wait
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass

    # Graceful shutdown
    hb_task.cancel()
    if comment_task:
        comment_task.cancel()
    if active_tasks:
        print(f"[WORKER] Waiting for {len(active_tasks)} in-flight jobs...")
        await asyncio.gather(*active_tasks, return_exceptions=True)

    await _deregister_worker(worker_id)
    print(f"[WORKER] {worker_id} shutdown complete")
