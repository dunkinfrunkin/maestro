"""API routes for agent run visibility — logs, status on tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from maestro.auth import get_current_user
from maestro.db.engine import get_session
from maestro.db.models import AgentRun, TaskPipelineRecord, User

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
