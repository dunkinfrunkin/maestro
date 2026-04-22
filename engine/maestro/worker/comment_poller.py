"""Polls open PRs for new human comments and dispatches implementation agents."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from maestro.db.engine import get_session
from maestro.db.models import (
    AgentRun,
    AgentRunStatus,
    PipelineStatus,
    TaskPipelineRecord,
    TrackerConnection,
    TrackerKind,
)
from maestro.db.encryption import decrypt_token

logger = logging.getLogger(__name__)

MAESTRO_BOT_MARKERS = ["maestro", "Co-Authored-By: Claude", "agent"]

REVIEWABLE_STATUSES = {
    PipelineStatus.REVIEW,
    PipelineStatus.RISK_PROFILE,
}


async def poll_comments_once() -> int:
    """Check all active PRs for new human comments. Returns count of tasks re-dispatched."""
    dispatched = 0

    async with get_session() as session:
        stmt = (
            select(TaskPipelineRecord)
            .where(TaskPipelineRecord.pr_url != "")
            .where(TaskPipelineRecord.pr_number != "")
            .where(TaskPipelineRecord.repo != "")
            .where(TaskPipelineRecord.status.in_([s.value for s in REVIEWABLE_STATUSES]))
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

    if tasks:
        logger.info("[comment-poller] Checking %d task(s) with open PRs", len(tasks))
    else:
        logger.debug("[comment-poller] No tasks with open PRs in reviewable status")

    for task in tasks:
        try:
            logger.debug(
                "[comment-poller] Checking %s PR #%s (%s) last_check=%s",
                task.repo, task.pr_number, task.status.value,
                task.last_comment_check_at.isoformat() if task.last_comment_check_at else "never",
            )
            has_new = await _check_for_new_human_comments(task)
            if has_new:
                logger.info(
                    "[comment-poller] New human comments on %s PR #%s - dispatching implementation agent",
                    task.repo, task.pr_number,
                )
                await _dispatch_for_comments(task)
                dispatched += 1
            else:
                logger.debug("[comment-poller] No new comments on %s PR #%s", task.repo, task.pr_number)
        except Exception:
            logger.exception("[comment-poller] Failed to check comments for task %s", task.external_ref)

    return dispatched


async def _check_for_new_human_comments(task: TaskPipelineRecord) -> bool:
    """Check if a PR has new unresolved human comments since last check."""
    since = task.last_comment_check_at

    comments = await _fetch_pr_comments(task)
    logger.debug("[comment-poller] Fetched %d total comments for %s PR #%s", len(comments), task.repo, task.pr_number)

    if not comments:
        await _update_check_timestamp(task.id)
        return False

    new_human_comments = []
    for comment in comments:
        created_at_str = comment.get("created_at") or comment.get("createdAt") or ""
        if not created_at_str:
            continue

        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        if since and created_at <= since:
            continue

        if comment.get("in_reply_to_id"):
            continue

        body = comment.get("body", "")
        user = comment.get("user", {}).get("login", "")

        if _is_maestro_comment(body, user):
            logger.debug("[comment-poller] Skipping agent comment by %s", user)
            continue

        logger.debug("[comment-poller] New human comment by %s: %s", user, body[:80])
        new_human_comments.append(comment)

    await _update_check_timestamp(task.id)

    if new_human_comments:
        logger.info("[comment-poller] Found %d new human comment(s) on %s PR #%s", len(new_human_comments), task.repo, task.pr_number)

    return len(new_human_comments) > 0


def _is_maestro_comment(body: str, user: str) -> bool:
    """Detect if a comment was made by Maestro agents."""
    lower_body = body.lower()
    lower_user = user.lower()
    for marker in MAESTRO_BOT_MARKERS:
        if marker.lower() in lower_body or marker.lower() in lower_user:
            return True
    if "[bot]" in lower_user:
        return True
    return False


async def _fetch_pr_comments(task: TaskPipelineRecord) -> list[dict]:
    """Fetch PR comments from the code host API."""
    async with get_session() as session:
        conn = await session.get(TrackerConnection, task.tracker_connection_id)
        if not conn:
            return []

    token = decrypt_token(conn.encrypted_token)

    if conn.kind == TrackerKind.GITHUB:
        return await _fetch_github_comments(task.repo, task.pr_number, token)
    elif conn.kind == TrackerKind.GITLAB:
        return await _fetch_gitlab_comments(task.repo, task.pr_number, token, conn.endpoint)

    return []


async def _fetch_github_comments(repo: str, pr_number: str, token: str) -> list[dict]:
    """Fetch review comments from GitHub PR."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "api", f"repos/{repo}/pulls/{pr_number}/comments",
        "--paginate",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_gh_env(token),
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("GitHub API error for %s PR #%s: %s", repo, pr_number, stderr.decode()[:200])
        return []

    try:
        return json.loads(stdout.decode())
    except json.JSONDecodeError:
        return []


async def _fetch_gitlab_comments(repo: str, mr_number: str, token: str, endpoint: str) -> list[dict]:
    """Fetch discussion notes from GitLab MR."""
    import urllib.parse
    encoded = urllib.parse.quote(repo, safe="")
    base = (endpoint or "https://gitlab.com").rstrip("/")
    url = f"{base}/api/v4/projects/{encoded}/merge_requests/{mr_number}/notes"

    proc = await asyncio.create_subprocess_exec(
        "curl", "-sf",
        "-H", f"PRIVATE-TOKEN: {token}",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return []

    try:
        notes = json.loads(stdout.decode())
        return [
            {
                "id": n.get("id"),
                "body": n.get("body", ""),
                "created_at": n.get("created_at", ""),
                "user": {"login": n.get("author", {}).get("username", "")},
            }
            for n in notes
            if not n.get("system", False)
        ]
    except json.JSONDecodeError:
        return []


def _gh_env(token: str) -> dict:
    """Build environment with GitHub token."""
    import os
    env = os.environ.copy()
    env["GH_TOKEN"] = token
    return env


async def _update_check_timestamp(task_id: int) -> None:
    """Update the last_comment_check_at timestamp."""
    async with get_session() as session:
        task = await session.get(TaskPipelineRecord, task_id)
        if task:
            task.last_comment_check_at = datetime.now(timezone.utc)
            await session.commit()


async def _dispatch_for_comments(task: TaskPipelineRecord) -> None:
    """Move task back to implement and dispatch the implementation agent."""
    from maestro.worker.dispatcher import dispatch_agent_for_status

    async with get_session() as session:
        record = await session.get(TaskPipelineRecord, task.id)
        if not record:
            return
        record.status = PipelineStatus.IMPLEMENT
        await session.commit()
        workspace_id = record.project_id

    await dispatch_agent_for_status(
        workspace_id=workspace_id,
        task_pipeline_id=task.id,
        status=PipelineStatus.IMPLEMENT.value,
        issue_title=task.external_ref,
        triggered_by="comment_poller",
    )


async def run_comment_poller(
    interval: float = 60.0,
    shutdown: asyncio.Event | None = None,
) -> None:
    """Background loop that polls for new human comments on open PRs."""
    _shutdown = shutdown or asyncio.Event()
    logger.info("[comment-poller] Started (interval=%.1fs)", interval)

    while not _shutdown.is_set():
        try:
            logger.debug("[comment-poller] Polling...")
            count = await poll_comments_once()
            if count > 0:
                logger.info("[comment-poller] Dispatched %d task(s)", count)
            else:
                logger.debug("[comment-poller] No new comments found")
        except Exception:
            logger.exception("[comment-poller] Poll error")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    logger.info("Comment poller stopped")
