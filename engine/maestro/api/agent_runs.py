"""API routes for agent run visibility — logs, status on tasks."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqlfunc

from maestro.auth import get_current_user
from maestro.db.engine import get_session
from maestro.db.models import AgentRun, AgentRunLog, AgentRunStatus, PipelineStatus, Project, TaskPipelineRecord, User, WorkerHeartbeat

router = APIRouter(prefix="/api/v1")


@router.get("/tasks/{external_ref:path}/runs")
async def get_task_runs(
    external_ref: str,
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get all agent runs for a specific task."""
    async with get_session() as session:
        # Find the pipeline record
        result = await session.execute(
            select(TaskPipelineRecord).where(TaskPipelineRecord.external_ref == external_ref)
        )
        record = result.scalar_one_or_none()
        if not record:
            return []

        # Get runs for this task
        runs_result = await session.execute(
            select(AgentRun)
            .where(AgentRun.task_pipeline_id == record.id)
            .order_by(AgentRun.created_at.desc())
        )
        runs = runs_result.scalars().all()

    return [
        {
            "id": r.id,
            "agent_type": r.agent_type.value if r.agent_type else "",
            "status": r.status.value if r.status else "",
            "model": r.model,
            "summary": r.summary,
            "error": r.error,
            "cost_usd": r.cost_usd,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "peak_memory_mb": r.peak_memory_mb,
            "avg_cpu_percent": r.avg_cpu_percent,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.get("/workspaces/{workspace_id}/active-runs")
async def get_active_runs(
    workspace_id: int,
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get currently running/pending agent runs for the Operations dashboard."""
    async with get_session() as session:
        result = await session.execute(
            select(AgentRun, TaskPipelineRecord)
            .join(TaskPipelineRecord, TaskPipelineRecord.id == AgentRun.task_pipeline_id)
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.status.in_(["PENDING", "RUNNING"]),
            )
            .order_by(AgentRun.created_at.desc())
        )
        rows = result.all()

    return [
        {
            "id": run.id,
            "agent_type": run.agent_type.value if run.agent_type else "",
            "status": run.status.value if run.status else "",
            "model": run.model,
            "task_ref": task.external_ref,
            "pipeline_status": task.status.value if task.status else "",
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
        for run, task in rows
    ]


@router.get("/workspaces/{workspace_id}/executions")
async def list_executions(
    workspace_id: int,
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all agent runs across all tasks for a workspace."""
    async with get_session() as session:
        stmt = (
            select(AgentRun, TaskPipelineRecord)
            .join(TaskPipelineRecord, TaskPipelineRecord.id == AgentRun.task_pipeline_id)
            .where(AgentRun.workspace_id == workspace_id)
        )
        if status:
            stmt = stmt.where(AgentRun.status == status)

        # Count total
        from sqlalchemy import func
        count_stmt = (
            select(func.count(AgentRun.id))
            .where(AgentRun.workspace_id == workspace_id)
        )
        if status:
            count_stmt = count_stmt.where(AgentRun.status == status)
        total = (await session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(AgentRun.created_at.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()

    return {
        "total": total,
        "executions": [
            {
                "id": run.id,
                "agent_type": run.agent_type.value if run.agent_type else "",
                "status": run.status.value if run.status else "",
                "model": run.model,
                "summary": run.summary,
                "error": run.error,
                "cost_usd": run.cost_usd,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "triggered_by": run.triggered_by or "",
                "task_ref": task.external_ref,
                "pipeline_status": task.status.value if task.status else "",
                "repo": task.repo or "",
            }
            for run, task in rows
        ],
    }


@router.post("/agent-runs/{run_id}/kill")
async def kill_agent_run(
    run_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """Kill a running agent process."""
    from maestro.agents.cli_runner import kill_run
    from datetime import datetime, timezone

    partial = await kill_run(run_id)

    # Update DB record regardless of whether process was found
    async with get_session() as session:
        run = await session.get(AgentRun, run_id)
        if run and run.status.value in ("running", "pending"):
            run.status = "FAILED"
            run.error = "Killed by user"
            run.finished_at = datetime.now(timezone.utc)
            if partial:
                run.cost_usd = partial.get("total_cost_usd", run.cost_usd)
                run.input_tokens = partial.get("input_tokens", run.input_tokens)
                run.output_tokens = partial.get("output_tokens", run.output_tokens)
                run.summary = partial.get("last_text", run.summary)
            await session.commit()
            return {"status": "killed", "run_id": run_id}

    if partial:
        return {"status": "killed", "run_id": run_id}
    return {"status": "not_found", "run_id": run_id}


@router.get("/workspaces/{workspace_id}/centcom")
async def get_centcom_metrics(
    workspace_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """Aggregate metrics for CENTCOM dashboard."""
    async with get_session() as session:
        base = select(AgentRun).where(AgentRun.workspace_id == workspace_id)

        # Total runs by status
        status_counts = {}
        for status in AgentRunStatus:
            count = (await session.execute(
                select(sqlfunc.count(AgentRun.id))
                .where(AgentRun.workspace_id == workspace_id, AgentRun.status == status)
            )).scalar() or 0
            status_counts[status.value] = count

        # Aggregates
        agg = (await session.execute(
            select(
                sqlfunc.count(AgentRun.id).label("total_runs"),
                sqlfunc.coalesce(sqlfunc.sum(AgentRun.cost_usd), 0).label("total_cost"),
                sqlfunc.coalesce(sqlfunc.sum(AgentRun.input_tokens), 0).label("total_input_tokens"),
                sqlfunc.coalesce(sqlfunc.sum(AgentRun.output_tokens), 0).label("total_output_tokens"),
                sqlfunc.coalesce(sqlfunc.max(AgentRun.peak_memory_mb), 0).label("peak_memory_mb"),
                sqlfunc.coalesce(sqlfunc.avg(AgentRun.avg_cpu_percent), 0).label("avg_cpu_percent"),
            ).where(AgentRun.workspace_id == workspace_id)
        )).one()

        # Total runtime (sum of finished - started for completed runs)
        runtime_rows = (await session.execute(
            select(AgentRun.started_at, AgentRun.finished_at)
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.started_at.isnot(None),
                AgentRun.finished_at.isnot(None),
            )
        )).all()
        total_runtime_s = sum(
            (r.finished_at - r.started_at).total_seconds()
            for r in runtime_rows
            if r.started_at and r.finished_at
        )

        # Total unique tasks that have completed
        tasks_completed = (await session.execute(
            select(sqlfunc.count(sqlfunc.distinct(AgentRun.task_pipeline_id)))
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.status == AgentRunStatus.COMPLETED,
            )
        )).scalar() or 0

        # Active runs (for the live list)
        active_result = await session.execute(
            select(AgentRun, TaskPipelineRecord)
            .join(TaskPipelineRecord, TaskPipelineRecord.id == AgentRun.task_pipeline_id)
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.status.in_(["PENDING", "RUNNING"]),
            )
            .order_by(AgentRun.created_at.desc())
            .limit(10)
        )
        active_rows = active_result.all()

        # Recent completed (last 5)
        recent_result = await session.execute(
            select(AgentRun, TaskPipelineRecord)
            .join(TaskPipelineRecord, TaskPipelineRecord.id == AgentRun.task_pipeline_id)
            .where(
                AgentRun.workspace_id == workspace_id,
                AgentRun.status.in_(["COMPLETED", "FAILED"]),
            )
            .order_by(AgentRun.finished_at.desc())
            .limit(5)
        )
        recent_rows = recent_result.all()

        # Polled MRs — tasks with open PRs in pollable statuses
        _pollable = {
            PipelineStatus.IN_PROGRESS,
            PipelineStatus.PENDING_APPROVAL,
            PipelineStatus.REVIEW,
            PipelineStatus.RISK_PROFILE,
        }
        polled_result = await session.execute(
            select(TaskPipelineRecord)
            .join(Project, Project.id == TaskPipelineRecord.project_id)
            .where(
                Project.workspace_id == workspace_id,
                TaskPipelineRecord.pr_url != "",
                TaskPipelineRecord.pr_number != "",
                TaskPipelineRecord.status.in_([s.value for s in _pollable]),
            )
            .order_by(TaskPipelineRecord.last_comment_check_at.desc().nullsfirst())
        )
        polled_tasks = polled_result.scalars().all()

    def _run_dict(run, task):
        return {
            "id": run.id,
            "agent_type": run.agent_type.value if run.agent_type else "",
            "status": run.status.value if run.status else "",
            "model": run.model,
            "cost_usd": run.cost_usd,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "peak_memory_mb": run.peak_memory_mb,
            "avg_cpu_percent": run.avg_cpu_percent,
            "triggered_by": run.triggered_by or "",
            "task_ref": task.external_ref,
            "repo": task.repo or "",
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }

    def _mr_dict(task):
        return {
            "external_ref": task.external_ref,
            "pr_url": task.pr_url,
            "pr_number": task.pr_number,
            "repo": task.repo or "",
            "status": task.status.value if task.status else "",
            "last_checked_at": task.last_comment_check_at.isoformat() if task.last_comment_check_at else None,
        }

    return {
        "total_runs": agg.total_runs,
        "total_cost": float(agg.total_cost),
        "total_input_tokens": int(agg.total_input_tokens),
        "total_output_tokens": int(agg.total_output_tokens),
        "total_runtime_seconds": total_runtime_s,
        "peak_memory_mb": float(agg.peak_memory_mb),
        "avg_cpu_percent": float(agg.avg_cpu_percent),
        "tasks_completed": tasks_completed,
        "status_counts": status_counts,
        "active_runs": [_run_dict(r, t) for r, t in active_rows],
        "recent_runs": [_run_dict(r, t) for r, t in recent_rows],
        "workers": await _get_workers(),
        "polled_mrs": [_mr_dict(t) for t in polled_tasks],
    }


async def _get_workers() -> list[dict]:
    """Get active workers (heartbeat within last 30s)."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=30)
    async with get_session() as session:
        result = await session.execute(
            select(WorkerHeartbeat).where(
                WorkerHeartbeat.last_heartbeat >= cutoff,
                WorkerHeartbeat.status == "online",
            )
        )
        workers = result.scalars().all()
    return [
        {
            "id": w.id,
            "hostname": w.hostname,
            "concurrency": w.concurrency,
            "active_jobs": w.active_jobs,
            "cpu_percent": w.cpu_percent,
            "memory_used_mb": w.memory_used_mb,
            "memory_total_mb": w.memory_total_mb,
            "cpu_count": w.cpu_count,
            "estimated_capacity": w.estimated_capacity,
            "started_at": w.started_at.isoformat() if w.started_at else None,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
        }
        for w in workers
    ]


@router.get("/agent-runs/{run_id}/logs")
async def get_run_logs(
    run_id: int,
    user: User = Depends(get_current_user),
    after_id: int = 0,
) -> list[dict]:
    """Get log entries for a specific agent run. Use after_id for polling new entries."""
    async with get_session() as session:
        stmt = (
            select(AgentRunLog)
            .where(AgentRunLog.agent_run_id == run_id)
        )
        if after_id > 0:
            stmt = stmt.where(AgentRunLog.id > after_id)
        stmt = stmt.order_by(AgentRunLog.id)

        result = await session.execute(stmt)
        logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "entry_type": log.entry_type,
            "content": log.content,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
