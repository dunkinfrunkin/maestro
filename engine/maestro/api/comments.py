"""API routes for PR/MR comments across all tasks."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from maestro.auth import get_current_user
from maestro.db import crud
from maestro.db.engine import get_session
from maestro.db.models import AgentRun, PipelineStatus, TaskPipelineRecord, TrackerKind, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.get("/comments")
async def list_comments(
    project_id: int | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Fetch recent PR/MR comments across all tasks.

    Aggregates comments from all open PRs/MRs in the project.
    source: 'human', 'agent', or None for all.
    """
    from sqlalchemy import select

    async with get_session() as session:
        stmt = (
            select(TaskPipelineRecord)
            .where(TaskPipelineRecord.pr_url != "")
            .where(TaskPipelineRecord.pr_number != "")
            .where(TaskPipelineRecord.repo != "")
        )
        if project_id:
            stmt = stmt.where(TaskPipelineRecord.project_id == project_id)
        stmt = stmt.order_by(TaskPipelineRecord.updated_at.desc()).limit(20)

        result = await session.execute(stmt)
        tasks = result.scalars().all()

    if not tasks:
        return []

    # Find a code host connection for fetching comments
    from maestro.worker.poller import _find_codehost_connection
    from maestro.db.encryption import decrypt_token

    # Pre-fetch triggered_by for each task from latest agent run
    task_triggered_by: dict[int, str] = {}
    async with get_session() as session:
        for task in tasks:
            from sqlalchemy import select
            result = await session.execute(
                select(AgentRun.triggered_by)
                .where(AgentRun.task_pipeline_id == task.id)
                .where(AgentRun.triggered_by != "")
                .order_by(AgentRun.created_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                task_triggered_by[task.id] = row

    all_comments: list[dict] = []

    for task in tasks:
        try:
            conn = await _find_codehost_connection(task)
            if not conn:
                continue

            token = decrypt_token(conn.encrypted_token)
            comments = await _fetch_comments_for_task(task, conn, token)

            for c in comments:
                is_agent = "Created by Maestro" in c.get("body", "")
                agent_type = None
                if "Implementation Agent" in c.get("body", ""):
                    agent_type = "implementation"
                elif "Review Agent" in c.get("body", ""):
                    agent_type = "review"
                elif "Risk Profile Agent" in c.get("body", ""):
                    agent_type = "risk_profile"

                if source == "human" and is_agent:
                    continue
                if source == "agent" and not is_agent:
                    continue

                all_comments.append({
                    "id": c.get("id", 0),
                    "task_ref": task.external_ref,
                    "task_title": task.external_ref.split(":")[-1],
                    "pr_url": task.pr_url,
                    "pr_number": task.pr_number,
                    "repo": task.repo,
                    "author": c.get("user", {}).get("login", "unknown"),
                    "triggered_by": task_triggered_by.get(task.id, ""),
                    "body": c.get("body", ""),
                    "is_agent": is_agent,
                    "agent_type": agent_type,
                    "url": c.get("html_url") or c.get("url"),
                    "file_path": c.get("path"),
                    "line_number": c.get("line"),
                    "created_at": c.get("created_at", ""),
                })
        except Exception:
            logger.exception("Failed to fetch comments for task %s", task.external_ref)

    all_comments.sort(key=lambda c: c["created_at"], reverse=True)
    return all_comments[:limit]


async def _fetch_comments_for_task(task: TaskPipelineRecord, conn, token: str) -> list[dict]:
    """Fetch comments from a PR/MR."""
    import asyncio
    from urllib.parse import quote

    if conn.kind == TrackerKind.GITLAB:
        endpoint = (conn.endpoint or "https://gitlab.com").rstrip("/")
        encoded = quote(task.repo, safe="")
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sf",
            "-H", f"PRIVATE-TOKEN: {token}",
            f"{endpoint}/api/v4/projects/{encoded}/merge_requests/{task.pr_number}/notes?sort=desc&per_page=50",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return []

        notes = json.loads(stdout.decode())
        return [
            {
                "id": n.get("id"),
                "body": n.get("body", ""),
                "created_at": n.get("created_at", ""),
                "user": {"login": n.get("author", {}).get("username", "")},
                "html_url": f"{task.pr_url}#note_{n.get('id', '')}",
                "path": None,
                "line": None,
            }
            for n in notes
            if not n.get("system", False)
        ]

    elif conn.kind == TrackerKind.GITHUB:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"repos/{task.repo}/pulls/{task.pr_number}/comments",
            "--paginate",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return []

        comments = json.loads(stdout.decode())
        return [
            {
                "id": c.get("id"),
                "body": c.get("body", ""),
                "created_at": c.get("created_at", ""),
                "user": {"login": c.get("user", {}).get("login", "")},
                "html_url": c.get("html_url"),
                "path": c.get("path"),
                "line": c.get("line"),
            }
            for c in comments
        ]

    return []
