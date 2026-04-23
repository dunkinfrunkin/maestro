"""API routes for tasks and tracker connections."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from maestro.auth import get_current_user
from maestro.db import crud
from maestro.db.engine import get_session
from maestro.db.models import AgentRunLog, PipelineStatus, TaskPipelineRecord, TrackerKind, User
from maestro.tracker.github import GitHubClient
from maestro.tracker.linear import LinearClient

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UnifiedTask(BaseModel):
    """Tracker-agnostic task representation."""
    id: int | None = None  # internal pipeline ID (set once task enters pipeline)
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
    pr_url: str | None = None
    repo: str | None = None  # associated repository (e.g., "owner/repo")


class ConnectionCreate(BaseModel):
    kind: str  # "github", "linear", "gitlab", or "jira"
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
    email: str = ""
    has_token: bool
    created_at: str


class PipelineStatusUpdate(BaseModel):
    status: str  # one of PipelineStatus values
    workspace_id: int | None = None
    project_id: int | None = None
    repo: str = ""
    issue_title: str = ""
    issue_description: str = ""
    issue_url: str = ""
    issue_identifier: str = ""


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
                email=c.email or "",
                has_token=bool(c.encrypted_token),
                created_at=c.created_at.isoformat() if c.created_at else "",
            )
            for c in conns
        ]


@router.post("/connections")
async def create_connection(body: ConnectionCreate, user: User = Depends(get_current_user)) -> ConnectionResponse:
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
            email=user.email,
            workspace_id=body.workspace_id,
        )
        return ConnectionResponse(
            id=conn.id,
            kind=conn.kind.value,
            name=conn.name,
            project=conn.project,
            endpoint=conn.endpoint,
            email=conn.email or "",
            has_token=True,
            created_at=conn.created_at.isoformat() if conn.created_at else "",
        )


class ConnectionUpdate(BaseModel):
    name: str | None = None
    project: str | None = None
    endpoint: str | None = None
    token: str | None = None


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: int, body: ConnectionUpdate) -> ConnectionResponse:
    """Update a connection's settings."""
    async with get_session() as session:
        conn = await crud.get_connection(session, connection_id)
        if not conn:
            raise HTTPException(status_code=404, detail="Connection not found")
        if body.name is not None:
            conn.name = body.name
        if body.project is not None:
            conn.project = body.project
        if body.endpoint is not None:
            conn.endpoint = body.endpoint
        if body.token is not None:
            from maestro.db.encryption import encrypt_token
            conn.encrypted_token = encrypt_token(body.token)
        await session.commit()
        await session.refresh(conn)
        return ConnectionResponse(
            id=conn.id,
            kind=conn.kind.value,
            name=conn.name,
            project=conn.project,
            endpoint=conn.endpoint,
            email=conn.email or "",
            has_token=bool(conn.encrypted_token),
            created_at=conn.created_at.isoformat() if conn.created_at else "",
        )


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int) -> dict:
    async with get_session() as session:
        ok = await crud.delete_connection(session, connection_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Connection not found")
        return {"status": "deleted"}


@router.get("/connections/{connection_id}/test")
async def test_connection(connection_id: int) -> dict:
    """Test a tracker connection by making a lightweight API call."""
    async with get_session() as session:
        conn = await crud.get_connection(session, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    token = crud.get_decrypted_token(conn)
    try:
        if conn.kind == TrackerKind.GITHUB:
            client = GitHubClient(token=token, endpoint=conn.endpoint or "https://api.github.com")
            try:
                await client.fetch_repos()
            finally:
                await client.close()

        elif conn.kind == TrackerKind.LINEAR:
            client = LinearClient(api_key=token, project_slug=conn.project, endpoint=conn.endpoint or "https://api.linear.app/graphql")
            try:
                await client.fetch_candidate_issues(max_results=1)
            finally:
                await client.close()

        elif conn.kind == TrackerKind.GITLAB:
            from maestro.external.gitlab.tracker import GitLabIssueTracker
            client = GitLabIssueTracker(token=token, group=conn.project, endpoint=conn.endpoint or "https://gitlab.com")
            try:
                await client.fetch_candidate_issues(max_results=1)
            finally:
                await client.close()

        elif conn.kind == TrackerKind.JIRA:
            from maestro.external.jira.tracker import JiraIssueTracker
            client = JiraIssueTracker(
                base_url=conn.endpoint or "https://jira.atlassian.net",
                api_token=token,
                project_key=conn.project or "",
                email=conn.email,
            )
            try:
                await client.fetch_candidate_issues(max_results=1)
            finally:
                await client.close()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tracker kind: {conn.kind.value}")

        return {"status": "ok", "message": "Connection successful"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/connections/{connection_id}/repos")
async def list_connection_repos(connection_id: int) -> list[dict]:
    """List repos/projects accessible via a connection's token."""
    async with get_session() as session:
        conn = await crud.get_connection(session, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    token = crud.get_decrypted_token(conn)

    if conn.kind == TrackerKind.GITHUB:
        client = GitHubClient(
            token=token,
            endpoint=conn.endpoint or "https://api.github.com",
        )
        try:
            return await client.fetch_repos()
        finally:
            await client.close()

    elif conn.kind == TrackerKind.GITLAB:
        from maestro.external.gitlab.tracker import GitLabIssueTracker
        client = GitLabIssueTracker(
            token=token,
            group=conn.project,
            endpoint=conn.endpoint or "https://gitlab.com",
        )
        try:
            return await client.fetch_projects()
        finally:
            await client.close()

    raise HTTPException(status_code=400, detail=f"{conn.kind.value} connections don't support repo listing")


@router.get("/repos")
async def list_all_repos(search: str | None = Query(None)) -> list[dict]:
    """List repos across all code-hosting connections (GitHub, GitLab).

    When `search` is provided it's passed to each tracker's native search
    API so filtering happens server-side and results come back fast.
    """
    import asyncio
    import logging

    log = logging.getLogger(__name__)

    async with get_session() as session:
        connections = await crud.list_connections(session)

    code_connections = [c for c in connections if c.kind in (TrackerKind.GITHUB, TrackerKind.GITLAB)]
    if not code_connections:
        return []

    async def _fetch_for_conn(conn) -> list[dict]:
        token = crud.get_decrypted_token(conn)
        try:
            if conn.kind == TrackerKind.GITHUB:
                client = GitHubClient(token=token, endpoint=conn.endpoint or "https://api.github.com", timeout_ms=10000)
                try:
                    repos = await client.fetch_repos(search=search or "")
                finally:
                    await client.close()
            elif conn.kind == TrackerKind.GITLAB:
                from maestro.external.gitlab.tracker import GitLabIssueTracker
                client = GitLabIssueTracker(
                    token=token, group=conn.project,
                    endpoint=conn.endpoint or "https://gitlab.com",
                    timeout_ms=10000,
                )
                try:
                    repos = await client.fetch_projects(search=search or "")
                finally:
                    await client.close()
            else:
                return []

            for repo in repos:
                repo["connection_id"] = conn.id
                repo["tracker_kind"] = conn.kind.value
            return repos
        except Exception as exc:
            log.warning("Failed to list repos from connection %s: %s", conn.name, exc)
            return [{
                "full_name": f"[Error: {conn.name}] {str(exc)[:100]}",
                "name": conn.name,
                "owner": "",
                "private": False,
                "open_issues_count": 0,
                "html_url": "",
                "connection_id": conn.id,
                "tracker_kind": f"{conn.kind.value} (error)",
            }]

    # Fetch from all connections in parallel with a 10s overall timeout
    tasks = [_fetch_for_conn(c) for c in code_connections]
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10.0)
    except asyncio.TimeoutError:
        return []

    all_repos: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            conn = code_connections[i]
            log.warning("Repo fetch failed for %s: %s", conn.name, result)
            all_repos.append({
                "full_name": f"[Error: {conn.name}] {str(result)[:100]}",
                "name": conn.name,
                "owner": "",
                "private": False,
                "open_issues_count": 0,
                "html_url": "",
                "connection_id": conn.id,
                "tracker_kind": f"{conn.kind.value} (error)",
            })
        else:
            all_repos.extend(result)

    return all_repos


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class PaginatedTasks(BaseModel):
    tasks: list[UnifiedTask]
    total: int
    offset: int
    limit: int


@router.get("/tasks")
async def list_tasks(
    connection_id: int | None = Query(None),
    search: str | None = Query(None),
    label: str | None = Query(None),
    pipeline_status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> PaginatedTasks:
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
            issues = await _fetch_from_tracker(conn, token, search, user_email=user.email, max_results=offset + limit)

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
                        id=record.id if record else None,
                        pipeline_status=record.status.value if record else None,
                        pr_url=record.pr_url if record and record.pr_url else None,
                        repo=record.repo if record and record.repo else None,
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

    # Sort newest first
    all_tasks.sort(key=lambda t: t.created_at or "", reverse=True)
    total = len(all_tasks)
    page = all_tasks[offset : offset + limit]
    return PaginatedTasks(tasks=page, total=total, offset=offset, limit=limit)


@router.put("/tasks/{external_ref:path}/status")
async def update_task_status(external_ref: str, body: PipelineStatusUpdate, user: User = Depends(get_current_user)) -> dict:
    """Set or update a task's pipeline status. Dispatches agent if applicable."""
    import logging as _log
    _log.getLogger(__name__).info(
        "[STATUS] ref=%s status=%s title=%r desc_len=%d url=%r",
        external_ref, body.status, body.issue_title, len(body.issue_description), body.issue_url,
    )
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
        record = await crud.set_pipeline_status(session, external_ref, conn_id, status, project_id=body.project_id or 0)
        # Save repo if provided
        if body.repo and not record.repo:
            record.repo = body.repo
            await session.commit()
            await session.refresh(record)

    # Dispatch agent for this status change
    agent_run_id = None
    if body.workspace_id:
        from maestro.worker.dispatcher import dispatch_agent_for_status
        agent_run_id = await dispatch_agent_for_status(
            workspace_id=body.workspace_id,
            task_pipeline_id=record.id,
            status=body.status,
            issue_title=body.issue_title,
            issue_description=body.issue_description,
            issue_url=body.issue_url,
            issue_identifier=body.issue_identifier,
            triggered_by=user.name or user.email,
        )

    return {
        "external_ref": record.external_ref,
        "status": record.status.value,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "agent_run_id": agent_run_id,
    }


@router.get("/pipeline/{pipeline_id}")
async def get_task_by_id(pipeline_id: int) -> dict:
    """Get a task by its internal pipeline ID."""
    async with get_session() as session:
        record = await session.get(TaskPipelineRecord, pipeline_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return await _build_task_detail(record)


@router.get("/tasks/{external_ref:path}/detail")
async def get_task_detail(external_ref: str) -> dict:
    """Get a single task with its pipeline info, fetched from the tracker."""
    async with get_session() as session:
        record = await crud.get_pipeline_record(session, external_ref)
    if record:
        return await _build_task_detail(record)
    # No pipeline record — still fetch from tracker
    return await _build_task_from_ref(external_ref)


async def _fetch_single_issue(conn, token: str, issue_id: str):
    """Fetch a single issue from any tracker type by its ID/key."""
    from maestro.models import Issue

    if conn.kind == TrackerKind.GITHUB:
        client = GitHubClient(token=token, repo=conn.project, endpoint=conn.endpoint or "https://api.github.com")
        try:
            # Try direct fetch by issue number if we have a repo
            if conn.project and issue_id.isdigit():
                issues = await client.search_issues(f"#{issue_id}")
                return next((i for i in issues if i.id == issue_id), None)
            issues = await client.fetch_candidate_issues(max_results=50)
            return next((i for i in issues if i.id == issue_id), None)
        finally:
            await client.close()

    elif conn.kind == TrackerKind.LINEAR:
        client = LinearClient(
            api_key=token, project_slug=conn.project,
            active_states=["Todo", "In Progress", "Done", "Canceled"],
            terminal_states=[],
            endpoint=conn.endpoint or "https://api.linear.app/graphql",
        )
        try:
            # Linear IDs are UUIDs — fetch states by ID to check it exists
            states = await client.fetch_issue_states_by_ids([issue_id])
            if not states:
                return None
            # Need full issue data — search candidate issues
            issues = await client.fetch_candidate_issues(max_results=50)
            return next((i for i in issues if i.id == issue_id), None)
        finally:
            await client.close()

    elif conn.kind == TrackerKind.GITLAB:
        from maestro.external.gitlab.tracker import GitLabIssueTracker
        client = GitLabIssueTracker(
            token=token, group=conn.project,
            endpoint=conn.endpoint or "https://gitlab.com",
        )
        try:
            issues = await client.fetch_candidate_issues(max_results=50)
            return next((i for i in issues if i.id == issue_id), None)
        finally:
            await client.close()

    elif conn.kind == TrackerKind.JIRA:
        from maestro.external.jira.tracker import JiraIssueTracker
        client = JiraIssueTracker(
            base_url=conn.endpoint or "https://jira.atlassian.net",
            api_token=token,
            project_key=conn.project or "",
            email=conn.email,
        )
        try:
            # Fetch by key (PROJ-123) or numeric id
            if "-" in issue_id:
                jql = f'key = "{issue_id}"'
            else:
                jql = f"id = {issue_id}"
            issues = await client._search(jql, max_results=1)
            if issues:
                return issues[0]
            return None
        finally:
            await client.close()

    return None


async def _build_task_from_ref(external_ref: str) -> dict:
    """Build task detail from external_ref without a pipeline record."""
    parts = external_ref.split(":")
    kind = parts[0] if len(parts) >= 1 else ""
    conn_id = int(parts[1]) if len(parts) >= 2 else 0
    issue_id = ":".join(parts[2:]) if len(parts) >= 3 else ""

    issue = None
    try:
        async with get_session() as session:
            conn = await crud.get_connection(session, conn_id)
        if conn:
            token = crud.get_decrypted_token(conn)
            issue = await _fetch_single_issue(conn, token, issue_id)
    except Exception:
        pass

    if issue:
        return {
            "id": None,
            "external_ref": external_ref,
            "tracker_kind": kind,
            "connection_id": conn_id,
            "identifier": issue.identifier,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state,
            "priority": issue.priority,
            "labels": issue.labels,
            "url": issue.url,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "pipeline_status": None,
            "pr_url": None,
            "repo": None,
        }

    raise HTTPException(status_code=404, detail="Task not found in tracker")


async def _build_task_detail(record) -> dict:
    """Build task detail dict from a pipeline record."""
    external_ref = record.external_ref
    parts = external_ref.split(":")
    kind = parts[0] if len(parts) >= 1 else ""
    conn_id = int(parts[1]) if len(parts) >= 2 else 0
    issue_id = ":".join(parts[2:]) if len(parts) >= 3 else ""

    # Try to fetch from tracker
    issue = None
    try:
        async with get_session() as session:
            conn = await crud.get_connection(session, conn_id)
        if conn:
            token = crud.get_decrypted_token(conn)
            issue = await _fetch_single_issue(conn, token, issue_id)
    except Exception:
        pass

    if issue:
        return {
            "id": record.id,
            "external_ref": external_ref,
            "tracker_kind": kind,
            "connection_id": conn_id,
            "identifier": issue.identifier,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state,
            "priority": issue.priority,
            "labels": issue.labels,
            "url": issue.url,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "pipeline_status": record.status.value if record.status else None,
            "pr_url": record.pr_url or None,
            "repo": record.repo or None,
        }

    return {
        "id": record.id,
        "external_ref": external_ref,
        "tracker_kind": kind,
        "connection_id": conn_id,
        "identifier": f"#{issue_id}",
        "title": "",
        "description": None,
        "state": "",
        "priority": None,
        "labels": [],
        "url": None,
        "created_at": None,
        "updated_at": None,
        "pipeline_status": record.status.value if record.status else None,
        "pr_url": record.pr_url or None,
        "repo": record.repo or None,
    }


@router.delete("/tasks/{external_ref:path}/status")
async def remove_task_status(external_ref: str) -> dict:
    """Remove a task from the pipeline (delete its record)."""
    async with get_session() as session:
        ok = await crud.delete_pipeline_record(session, external_ref)
        if not ok:
            raise HTTPException(status_code=404, detail="No pipeline record for this task")
        return {"status": "removed"}


class TaskPrUrlUpdateBody(BaseModel):
    pr_url: str


@router.get("/tasks/{external_ref:path}/pr_url")
async def get_task_pr_url(external_ref: str) -> dict:
    """Get the current PR/MR URL for a task without hitting the tracker."""
    async with get_session() as session:
        record = await crud.get_pipeline_record(session, external_ref)
    return {"pr_url": record.pr_url or None if record else None}


@router.put("/tasks/{external_ref:path}/pr_url")
async def update_task_pr_url(external_ref: str, body: TaskPrUrlUpdateBody) -> dict:
    """Set or update the MR/PR URL associated with a task."""
    async with get_session() as session:
        record = await crud.get_pipeline_record(session, external_ref)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        pr_url = body.pr_url.strip()
        record.pr_url = pr_url
        record.pr_number = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
        await session.commit()
        return {"external_ref": external_ref, "pr_url": record.pr_url}


class TaskRepoUpdate(BaseModel):
    repo: str


class TaskRepoUpdateBody(BaseModel):
    repo: str
    project_id: int | None = None


@router.put("/tasks/{external_ref:path}/repo")
async def update_task_repo(external_ref: str, body: TaskRepoUpdateBody) -> dict:
    """Set or update the repository associated with a task.

    Creates a pipeline record if one doesn't exist (status defaults to queued).
    """
    async with get_session() as session:
        record = await crud.get_pipeline_record(session, external_ref)
        if not record:
            project_id = body.project_id
            if not project_id:
                from sqlalchemy import select
                from maestro.db.models import Project
                first = (await session.execute(select(Project).limit(1))).scalar()
                if not first:
                    raise HTTPException(status_code=400, detail="No project exists yet")
                project_id = first.id
            parts = external_ref.split(":")
            conn_id = int(parts[1]) if len(parts) >= 2 else 0
            record = TaskPipelineRecord(
                external_ref=external_ref,
                tracker_connection_id=conn_id,
                status=PipelineStatus.QUEUED,
                project_id=project_id,
            )
            session.add(record)
            await session.flush()
        record.repo = body.repo
        await session.commit()
        return {"external_ref": external_ref, "repo": record.repo}


class RequirementsAgentBody(BaseModel):
    workspace_id: int | None = None
    project_id: int | None = None
    issue_title: str = ""
    issue_description: str = ""
    issue_url: str = ""
    issue_identifier: str = ""


@router.post("/tasks/{external_ref:path}/requirements")
async def trigger_requirements_agent(
    request: Request,
    external_ref: str,
    body: RequirementsAgentBody,
) -> dict:
    """Manually trigger the requirements agent for a task."""
    from maestro.worker.dispatcher import dispatch_requirements_agent

    workspace_id = body.workspace_id
    if not workspace_id:
        async with get_session() as session:
            from sqlalchemy import select
            from maestro.db.models import Workspace
            ws = (await session.execute(select(Workspace).limit(1))).scalar()
            if not ws:
                raise HTTPException(status_code=400, detail="No workspace found")
            workspace_id = ws.id

    # Ensure pipeline record exists
    async with get_session() as session:
        record = await crud.get_pipeline_record(session, external_ref)
        if not record:
            project_id = body.project_id
            if not project_id:
                from sqlalchemy import select
                from maestro.db.models import Project
                first = (await session.execute(select(Project).limit(1))).scalar()
                if not first:
                    raise HTTPException(status_code=400, detail="No project exists yet")
                project_id = first.id
            parts = external_ref.split(":")
            conn_id = int(parts[1]) if len(parts) >= 2 else 0
            record = TaskPipelineRecord(
                external_ref=external_ref,
                tracker_connection_id=conn_id,
                status=PipelineStatus.QUEUED,
                project_id=project_id,
            )
            session.add(record)
            await session.flush()
            await session.commit()
            await session.refresh(record)
        task_pipeline_id = record.id

    run_id = await dispatch_requirements_agent(
        workspace_id=workspace_id,
        task_pipeline_id=task_pipeline_id,
        issue_title=body.issue_title,
        issue_description=body.issue_description,
        issue_url=body.issue_url,
        issue_identifier=body.issue_identifier,
        triggered_by="user",
    )
    if run_id is None:
        raise HTTPException(status_code=400, detail="Failed to dispatch requirements agent (check API key)")
    return {"agent_run_id": run_id}


class AgentPromptBody(BaseModel):
    content: str


@router.post("/agent-runs/{run_id}/prompt")
async def send_agent_prompt(run_id: int, body: AgentPromptBody) -> dict:
    """Send a user prompt to a running agent (e.g., requirements agent waiting for input)."""
    async with get_session() as session:
        log = AgentRunLog(
            agent_run_id=run_id,
            entry_type="user_prompt",
            content=body.content,
        )
        session.add(log)
        await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_from_tracker(conn: Any, token: str, search: str | None, user_email: str = "", max_results: int = 100):
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
            return await client.fetch_candidate_issues(max_results=max_results)
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
            return await client.fetch_candidate_issues(max_results=max_results)
        finally:
            await client.close()

    elif conn.kind == TrackerKind.GITLAB:
        from maestro.external.gitlab.tracker import GitLabIssueTracker
        client = GitLabIssueTracker(
            token=token,
            group=conn.project,  # project field stores the group path
            endpoint=conn.endpoint or "https://gitlab.com",
        )
        try:
            if search:
                return await client.search_issues(search)
            return await client.fetch_candidate_issues(max_results=max_results)
        finally:
            await client.close()

    elif conn.kind == TrackerKind.JIRA:
        from maestro.external.jira.tracker import JiraIssueTracker
        client = JiraIssueTracker(
            base_url=conn.endpoint or "https://jira.atlassian.net",
            api_token=token,
            project_key=conn.project,  # project field stores comma-separated keys
            email=conn.email,  # Jira Cloud basic auth
            assignee_email=user_email,
        )
        try:
            if search:
                return await client.search_issues(search)
            return await client.fetch_candidate_issues(max_results=max_results)
        finally:
            await client.close()

    return []
