"""API routes for tasks and tracker connections."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from maestro.db import crud
from maestro.db.engine import get_session
from maestro.db.models import PipelineStatus, TrackerKind
from maestro.tracker.github import GitHubClient
from maestro.tracker.linear import LinearClient

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UnifiedTask(BaseModel):
    """Tracker-agnostic task representation."""
    external_ref: str
    tracker_kind: str
    connection_id: int
    identifier: str
    title: str
    description: str | None = None
    state: str  # tracker's native state
    priority: int | None = None
    labels: list[str] = []
    url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    pipeline_status: str | None = None  # our harness engineering status


class ConnectionCreate(BaseModel):
    kind: str  # "github" or "linear"
    name: str
    project: str = ""  # optional for GitHub (access all repos)
    token: str
    endpoint: str = ""
    workspace_id: int | None = None


class ConnectionResponse(BaseModel):
    id: int
    kind: str
    name: str
    project: str
    endpoint: str
    has_token: bool
    created_at: str


class PipelineStatusUpdate(BaseModel):
    status: str  # one of PipelineStatus values
    workspace_id: int | None = None
    issue_title: str = ""
    issue_description: str = ""
    issue_url: str = ""


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------


@router.get("/connections")
async def list_connections() -> list[ConnectionResponse]:
    async with get_session() as session:
        conns = await crud.list_connections(session)
        return [
            ConnectionResponse(
                id=c.id,
                kind=c.kind.value,
                name=c.name,
                project=c.project,
                endpoint=c.endpoint,
                has_token=bool(c.encrypted_token),
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
            for c in conns
        ]


@router.post("/connections")
async def create_connection(body: ConnectionCreate) -> ConnectionResponse:
    try:
        kind = TrackerKind(body.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tracker kind: {body.kind}")

    async with get_session() as session:
        conn = await crud.create_connection(
            session,
            kind=kind,
            name=body.name,
            project=body.project,
            token=body.token,
            endpoint=body.endpoint,
            workspace_id=body.workspace_id,
        )
        return ConnectionResponse(
            id=conn.id,
            kind=conn.kind.value,
            name=conn.name,
            project=conn.project,
            endpoint=conn.endpoint,
            has_token=True,
            created_at=conn.created_at.isoformat() if conn.created_at else "",
        )


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int) -> dict:
    async with get_session() as session:
        ok = await crud.delete_connection(session, connection_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Connection not found")
        return {"status": "deleted"}


@router.get("/connections/{connection_id}/repos")
async def list_connection_repos(connection_id: int) -> list[dict]:
    """List repos accessible via a GitHub connection's token."""
    async with get_session() as session:
        conn = await crud.get_connection(session, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    if conn.kind != TrackerKind.GITHUB:
        raise HTTPException(status_code=400, detail="Only GitHub connections support repo listing")

    token = crud.get_decrypted_token(conn)
    client = GitHubClient(
        token=token,
        endpoint=conn.endpoint or "https://api.github.com",
    )
    try:
        return await client.fetch_repos()
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.get("/tasks")
async def list_tasks(
    connection_id: int | None = Query(None),
    search: str | None = Query(None),
    label: str | None = Query(None),
    pipeline_status: str | None = Query(None),
) -> list[UnifiedTask]:
    """Fetch tasks from connected tracker(s) with optional search/filter."""
    async with get_session() as session:
        connections = await crud.list_connections(session)

    if connection_id is not None:
        connections = [c for c in connections if c.id == connection_id]

    if not connections:
        return []

    all_tasks: list[UnifiedTask] = []

    for conn in connections:
        try:
            token = crud.get_decrypted_token(conn)
            issues = await _fetch_from_tracker(conn, token, search)

            # Load pipeline records for these issues
            async with get_session() as session:
                for issue in issues:
                    ext_ref = f"{conn.kind.value}:{conn.id}:{issue.id}"
                    record = await crud.get_pipeline_record(session, ext_ref)

                    task = UnifiedTask(
                        external_ref=ext_ref,
                        tracker_kind=conn.kind.value,
                        connection_id=conn.id,
                        identifier=issue.identifier,
                        title=issue.title,
                        description=issue.description,
                        state=issue.state,
                        priority=issue.priority,
                        labels=issue.labels,
                        url=issue.url,
                        created_at=issue.created_at.isoformat() if issue.created_at else None,
                        updated_at=issue.updated_at.isoformat() if issue.updated_at else None,
                        pipeline_status=record.status.value if record else None,
                    )

                    # Apply filters
                    if label and label.lower() not in task.labels:
                        continue
                    if pipeline_status:
                        if pipeline_status == "none" and task.pipeline_status is not None:
                            continue
                        elif pipeline_status != "none" and task.pipeline_status != pipeline_status:
                            continue

                    all_tasks.append(task)
        except Exception as exc:
            # Log but don't fail entire request if one connection errors
            import logging
            logging.getLogger(__name__).exception(
                "Failed to fetch from connection %s (%s)", conn.name, conn.kind.value
            )

    return all_tasks


@router.put("/tasks/{external_ref:path}/status")
async def update_task_status(external_ref: str, body: PipelineStatusUpdate) -> dict:
    """Set or update a task's pipeline status. Dispatches agent if applicable."""
    try:
        status = PipelineStatus(body.status)
    except ValueError:
        valid = [s.value for s in PipelineStatus]
        raise HTTPException(
            status_code=400, detail=f"Invalid status: {body.status}. Valid: {valid}"
        )

    # Extract connection_id from external_ref (format: "kind:conn_id:issue_id")
    parts = external_ref.split(":")
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid external_ref format")
    try:
        conn_id = int(parts[1])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid connection_id in external_ref")

    async with get_session() as session:
        record = await crud.set_pipeline_status(session, external_ref, conn_id, status)

    # Dispatch agent for this status change
    agent_run_id = None
    if body.workspace_id:
        from maestro.agent.dispatcher import dispatch_agent_for_status
        agent_run_id = await dispatch_agent_for_status(
            workspace_id=body.workspace_id,
            task_pipeline_id=record.id,
            status=body.status,
            issue_title=body.issue_title,
            issue_description=body.issue_description,
            issue_url=body.issue_url,
        )

    return {
        "external_ref": record.external_ref,
        "status": record.status.value,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "agent_run_id": agent_run_id,
    }


@router.delete("/tasks/{external_ref:path}/status")
async def remove_task_status(external_ref: str) -> dict:
    """Remove a task from the pipeline (delete its record)."""
    async with get_session() as session:
        ok = await crud.delete_pipeline_record(session, external_ref)
        if not ok:
            raise HTTPException(status_code=404, detail="No pipeline record for this task")
        return {"status": "removed"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_from_tracker(conn: Any, token: str, search: str | None):
    """Fetch issues from a tracker connection."""
    from maestro.models import Issue

    if conn.kind == TrackerKind.GITHUB:
        client = GitHubClient(
            token=token,
            repo=conn.project,
            endpoint=conn.endpoint or "https://api.github.com",
        )
        try:
            if search:
                return await client.search_issues(search)
            return await client.fetch_candidate_issues()
        finally:
            await client.close()

    elif conn.kind == TrackerKind.LINEAR:
        client = LinearClient(
            api_key=token,
            project_slug=conn.project,
            active_states=["Todo", "In Progress"],
            terminal_states=["Done", "Canceled"],
            endpoint=conn.endpoint or "https://api.linear.app/graphql",
        )
        try:
            return await client.fetch_candidate_issues()
        finally:
            await client.close()

    return []
