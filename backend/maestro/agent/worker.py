"""Worker process — claims and executes agent jobs from the PostgreSQL queue."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys

from maestro.db.engine import get_session, init_db
from maestro.db.models import AgentRun, AgentRunStatus, ApiKeyProvider
from maestro.db import crud
from maestro.agent.plugin import registry, init_plugins

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
    from maestro.agent.dispatcher import _execute_agent
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


async def run_worker(concurrency: int = 3, poll_interval: float = 2.0) -> None:
    """Main worker loop — claims and executes agent jobs."""
    await init_db()
    init_plugins()

    semaphore = asyncio.Semaphore(concurrency)
    active_tasks: set[asyncio.Task] = set()
    shutdown = asyncio.Event()

    def handle_signal():
        print("[WORKER] Shutdown signal received, draining...")
        shutdown.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    print(f"[WORKER] Started (concurrency={concurrency}, poll_interval={poll_interval}s)")

    while not shutdown.is_set():
        # Clean up finished tasks
        done = {t for t in active_tasks if t.done()}
        for t in done:
            try:
                t.result()  # Raise any exceptions
            except Exception as e:
                logger.exception("Worker task failed: %s", e)
        active_tasks -= done

        # Try to claim a job if we have capacity
        if semaphore._value > 0:  # Check available slots
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
                continue  # Check for more jobs immediately

        # No job or at capacity — wait
        try:
            await asyncio.wait_for(shutdown.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass

    # Graceful shutdown: wait for in-flight jobs
    if active_tasks:
        print(f"[WORKER] Waiting for {len(active_tasks)} in-flight jobs...")
        await asyncio.gather(*active_tasks, return_exceptions=True)

    print("[WORKER] Shutdown complete")
