"""Polls open PRs for new human comments and stale branches, dispatching agents as needed."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

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

MAESTRO_FOOTER = "Created by Maestro"

POLLABLE_STATUSES = {
    PipelineStatus.IN_PROGRESS,
    PipelineStatus.PENDING_APPROVAL,
    # Legacy
    PipelineStatus.REVIEW,
    PipelineStatus.RISK_PROFILE,
}


async def _has_active_or_recent_agent_run(task_pipeline_id: int) -> bool:
    """Check if there's a running/pending agent run or one that completed very recently.

    The 'recently completed' check prevents races with auto-transition:
    when a review agent finishes, auto-transition dispatches the next agent.
    If the poller checks in that window, it would also dispatch,
    creating a duplicate.
    """
    from sqlalchemy import or_

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)

    async with get_session() as session:
        stmt = (
            select(AgentRun)
            .where(AgentRun.task_pipeline_id == task_pipeline_id)
            .where(or_(
                AgentRun.status.in_([
                    AgentRunStatus.PENDING.value,
                    AgentRunStatus.RUNNING.value,
                ]),
                AgentRun.finished_at > cutoff,
            ))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def poll_comments_once() -> int:
    """Check all active PRs for new human comments and stale branches. Returns count of tasks re-dispatched."""
    dispatched = 0

    async with get_session() as session:
        stmt = (
            select(TaskPipelineRecord)
            .where(TaskPipelineRecord.pr_url != "")
            .where(TaskPipelineRecord.pr_number != "")
            .where(TaskPipelineRecord.repo != "")
            .where(TaskPipelineRecord.status.in_([s.value for s in POLLABLE_STATUSES]))
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

    if tasks:
        logger.info("[poller] Checking %d task(s) with open PRs", len(tasks))
    else:
        logger.debug("[poller] No tasks with open PRs in reviewable status")

    dispatched_ids: set[int] = set()

    for task in tasks:
        try:
            pr_state = await _fetch_pr_state(task)
            if pr_state in ("closed", "merged"):
                logger.info("[poller] PR #%s on %s is %s — removing from poll list", task.pr_number, task.repo, pr_state)
                await _clear_pr_fields(task.id)
                continue

            if await _has_active_or_recent_agent_run(task.id):
                logger.debug("[poller] Skipping %s PR #%s - agent active or recently finished", task.repo, task.pr_number)
                continue

            logger.debug(
                "[poller] Checking %s PR #%s (%s) last_check=%s",
                task.repo, task.pr_number, task.status.value,
                task.last_comment_check_at.isoformat() if task.last_comment_check_at else "never",
            )
            has_new = await _check_for_new_human_comments(task)
            if has_new:
                logger.info(
                    "[poller] New human comments on %s PR #%s - dispatching implementation agent",
                    task.repo, task.pr_number,
                )
                await _dispatch_for_comments(task)
                dispatched_ids.add(task.id)
                dispatched += 1
            else:
                logger.debug("[poller] No new comments on %s PR #%s", task.repo, task.pr_number)
        except Exception:
            logger.exception("[poller] Failed to check comments for task %s", task.external_ref)

    for task in tasks:
        if task.id in dispatched_ids:
            continue
        try:
            if await _has_active_or_recent_agent_run(task.id):
                continue

            needs_rebase = await _check_needs_rebase(task)
            if needs_rebase:
                logger.info("[poller] Base branch updated for %s PR #%s - dispatching rebase", task.repo, task.pr_number)
                await _dispatch_for_rebase(task)
                dispatched += 1
            else:
                logger.debug("[poller] Base branch unchanged for %s PR #%s", task.repo, task.pr_number)
        except Exception:
            logger.exception("[poller] Failed to check rebase for task %s", task.external_ref)

    return dispatched


async def _check_for_new_human_comments(task: TaskPipelineRecord) -> bool:
    """Check if a PR has new unresolved human comments since last check."""
    since = task.last_comment_check_at

    comments = await _fetch_pr_comments(task)
    logger.debug("[poller] Fetched %d total comments for %s PR #%s", len(comments), task.repo, task.pr_number)

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
            logger.debug("[poller] Skipping agent comment by %s", user)
            continue

        logger.debug("[poller] New human comment by %s: %s", user, body[:80])
        new_human_comments.append(comment)

    await _update_check_timestamp(task.id)

    if new_human_comments:
        logger.info("[poller] Found %d new human comment(s) on %s PR #%s", len(new_human_comments), task.repo, task.pr_number)

    return len(new_human_comments) > 0


def _is_maestro_comment(body: str, user: str) -> bool:
    """Detect if a comment was made by Maestro agents."""
    if MAESTRO_FOOTER in body:
        return True
    if "created by Maestro" in body:
        return True
    if "[bot]" in user.lower():
        return True
    return False


async def _fetch_pr_comments(task: TaskPipelineRecord) -> list[dict]:
    """Fetch PR comments from the code host API based on pr_url domain."""
    if not task.pr_url:
        return []

    conn = await _find_codehost_connection(task)
    if not conn:
        logger.debug("[poller] No code host connection found for %s", task.pr_url)
        return []

    token = decrypt_token(conn.encrypted_token)

    if conn.kind == TrackerKind.GITHUB:
        return await _fetch_github_comments(task.repo, task.pr_number, token)
    elif conn.kind == TrackerKind.GITLAB:
        return await _fetch_gitlab_comments(task.repo, task.pr_number, token, conn.endpoint)

    return []


async def _find_codehost_connection(task: TaskPipelineRecord) -> TrackerConnection | None:
    """Find a code host connection matching the PR URL domain."""
    from urllib.parse import urlparse
    pr_domain = urlparse(task.pr_url).hostname or ""

    async with get_session() as session:
        stmt = select(TrackerConnection).where(
            TrackerConnection.kind.in_([TrackerKind.GITHUB.value, TrackerKind.GITLAB.value])
        )
        result = await session.execute(stmt)
        conns = result.scalars().all()

    for conn in conns:
        conn_domain = ""
        if conn.kind == TrackerKind.GITHUB:
            conn_domain = urlparse(conn.endpoint or "https://github.com").hostname or "github.com"
        elif conn.kind == TrackerKind.GITLAB:
            conn_domain = urlparse(conn.endpoint or "https://gitlab.com").hostname or "gitlab.com"

        if conn_domain and conn_domain == pr_domain:
            logger.debug("[poller] Matched connection %d (%s) for %s", conn.id, conn.kind.value, pr_domain)
            return conn

    return None


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


async def _fetch_pr_state(task: TaskPipelineRecord) -> str:
    """Return the PR state: 'open', 'closed', or 'merged'. Returns 'open' on failure."""
    conn = await _find_codehost_connection(task)
    if not conn:
        return "open"

    token = decrypt_token(conn.encrypted_token)

    if conn.kind == TrackerKind.GITHUB:
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"repos/{task.repo}/pulls/{task.pr_number}",
            "--jq", ".state + \":\" + (.merged // false | tostring)",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_gh_env(token),
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return "open"
        output = stdout.decode().strip()
        state, _, merged = output.partition(":")
        if merged == "true":
            return "merged"
        return state or "open"

    elif conn.kind == TrackerKind.GITLAB:
        import urllib.parse
        encoded = urllib.parse.quote(task.repo, safe="")
        base = (conn.endpoint or "https://gitlab.com").rstrip("/")
        url = f"{base}/api/v4/projects/{encoded}/merge_requests/{task.pr_number}"
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sf", "-H", f"PRIVATE-TOKEN: {token}", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return "open"
        try:
            data = json.loads(stdout.decode())
            return data.get("state", "open")
        except json.JSONDecodeError:
            return "open"

    return "open"


async def _clear_pr_fields(task_id: int) -> None:
    """Clear pr_url and pr_number so the task is never polled again."""
    async with get_session() as session:
        task = await session.get(TaskPipelineRecord, task_id)
        if task:
            task.pr_url = ""
            task.pr_number = ""
            await session.commit()


async def _update_check_timestamp(task_id: int) -> None:
    """Update the last_comment_check_at timestamp."""
    async with get_session() as session:
        task = await session.get(TaskPipelineRecord, task_id)
        if task:
            task.last_comment_check_at = datetime.now(timezone.utc)
            await session.commit()


async def _fetch_base_branch_sha(task: TaskPipelineRecord) -> str | None:
    """Fetch the current HEAD SHA of the PR/MR's target (base) branch."""
    conn = await _find_codehost_connection(task)
    if not conn:
        return None

    token = decrypt_token(conn.encrypted_token)

    if conn.kind == TrackerKind.GITHUB:
        return await _fetch_github_base_sha(task.repo, task.pr_number, token)
    elif conn.kind == TrackerKind.GITLAB:
        return await _fetch_gitlab_base_sha(task.repo, task.pr_number, token, conn.endpoint)

    return None


async def _fetch_github_base_sha(repo: str, pr_number: str, token: str) -> str | None:
    """Get the current HEAD SHA of the base branch via the GitHub PR object."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "api", f"repos/{repo}/pulls/{pr_number}",
        "--jq", ".base.sha",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_gh_env(token),
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("[poller] GitHub API error fetching base SHA for %s PR #%s: %s", repo, pr_number, stderr.decode()[:200])
        return None
    sha = stdout.decode().strip()
    return sha if sha else None


async def _fetch_gitlab_base_sha(repo: str, mr_number: str, token: str, endpoint: str) -> str | None:
    """Get the current HEAD SHA of the base branch via the GitLab MR object."""
    import urllib.parse
    encoded = urllib.parse.quote(repo, safe="")
    base = (endpoint or "https://gitlab.com").rstrip("/")
    url = f"{base}/api/v4/projects/{encoded}/merge_requests/{mr_number}"

    proc = await asyncio.create_subprocess_exec(
        "curl", "-sf",
        "-H", f"PRIVATE-TOKEN: {token}",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    if proc.returncode != 0:
        return None

    try:
        mr = json.loads(stdout.decode())
        diff_refs = mr.get("diff_refs") or {}
        return diff_refs.get("base_sha") or None
    except json.JSONDecodeError:
        return None


async def _check_needs_rebase(task: TaskPipelineRecord) -> bool:
    """Return True if the base branch has moved ahead since we last recorded its SHA."""
    current_sha = await _fetch_base_branch_sha(task)
    if not current_sha:
        return False

    if not task.base_branch_sha:
        # First time seeing this PR — record the SHA, no rebase needed yet
        async with get_session() as session:
            record = await session.get(TaskPipelineRecord, task.id)
            if record:
                record.base_branch_sha = current_sha
                await session.commit()
        return False

    if current_sha != task.base_branch_sha:
        logger.debug("[poller] Base SHA changed for %s PR #%s: %s -> %s", task.repo, task.pr_number, task.base_branch_sha[:8], current_sha[:8])
        async with get_session() as session:
            record = await session.get(TaskPipelineRecord, task.id)
            if record:
                record.base_branch_sha = current_sha
                await session.commit()
        return True

    return False


async def _dispatch_for_comments(task: TaskPipelineRecord) -> None:
    """Move task back to implement and dispatch the implementation agent."""
    from maestro.worker.dispatcher import dispatch_agent_for_status
    from maestro.db.models import Project

    async with get_session() as session:
        record = await session.get(TaskPipelineRecord, task.id)
        if not record:
            logger.warning("[poller] Task %d not found, skipping dispatch", task.id)
            return

        if record.status not in POLLABLE_STATUSES or not record.pr_url:
            logger.info("[poller] Task %s is now %s / pr_url=%r — skipping comment dispatch", task.external_ref, record.status, record.pr_url)
            return

        project = await session.get(Project, record.project_id)
        if not project:
            logger.warning("[poller] Project %d not found for task %d, skipping", record.project_id, task.id)
            return

        workspace_id = project.workspace_id
        record.status = PipelineStatus.IN_PROGRESS
        await session.commit()

    logger.info(
        "[poller] Moved task %s to implement (workspace=%d, pipeline=%d)",
        task.external_ref, workspace_id, task.id,
    )

    result = await dispatch_agent_for_status(
        workspace_id=workspace_id,
        task_pipeline_id=task.id,
        status=PipelineStatus.IN_PROGRESS.value,
        issue_title=task.external_ref,
        triggered_by="comment_poller",
    )

    if result:
        logger.info("[poller] Dispatched agent run %d for task %s", result, task.external_ref)
    else:
        logger.warning("[poller] Dispatch returned None for task %s - agent may be disabled or no API key", task.external_ref)


async def _dispatch_for_rebase(task: TaskPipelineRecord) -> None:
    """Dispatch the implementation agent to rebase the PR branch onto the updated base."""
    from maestro.worker.dispatcher import dispatch_agent_for_status
    from maestro.db.models import Project

    async with get_session() as session:
        record = await session.get(TaskPipelineRecord, task.id)
        if not record:
            logger.warning("[poller] Task %d not found, skipping rebase dispatch", task.id)
            return

        if record.status not in POLLABLE_STATUSES or not record.pr_url:
            logger.info("[poller] Task %s is now %s / pr_url=%r — skipping rebase dispatch", task.external_ref, record.status, record.pr_url)
            return

        project = await session.get(Project, record.project_id)
        if not project:
            logger.warning("[poller] Project %d not found for task %d, skipping rebase dispatch", record.project_id, task.id)
            return

        workspace_id = project.workspace_id
        record.status = PipelineStatus.IN_PROGRESS
        await session.commit()

    logger.info(
        "[poller] Moved task %s to implement for rebase (workspace=%d, pipeline=%d)",
        task.external_ref, workspace_id, task.id,
    )

    result = await dispatch_agent_for_status(
        workspace_id=workspace_id,
        task_pipeline_id=task.id,
        status=PipelineStatus.IN_PROGRESS.value,
        issue_title=task.external_ref,
        triggered_by="rebase_poller",
    )

    if result:
        logger.info("[poller] Dispatched rebase agent run %d for task %s", result, task.external_ref)
    else:
        logger.warning("[poller] Rebase dispatch returned None for task %s", task.external_ref)


POLLER_LOCK_ID = 73572


async def _try_poll_with_lock() -> int:
    """Acquire a session-level advisory lock, poll, then release.

    Uses pg_try_advisory_lock / pg_advisory_unlock (session-level) so the
    lock persists across multiple statements for the full duration of the
    poll, preventing any other worker from entering concurrently.
    """
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(f"SELECT pg_try_advisory_lock({POLLER_LOCK_ID})")
        )
        acquired = result.scalar() or False
        if not acquired:
            return -1  # another worker is polling right now

    try:
        return await poll_comments_once()
    finally:
        try:
            async with get_session() as session:
                await session.execute(text(f"SELECT pg_advisory_unlock({POLLER_LOCK_ID})"))
                await session.commit()
        except Exception:
            logger.warning("[poller] Failed to release advisory lock %d", POLLER_LOCK_ID)


async def run_comment_poller(
    interval: float = 60.0,
    shutdown: asyncio.Event | None = None,
) -> None:
    """Background loop that polls for new human comments and stale branches on open PRs.

    Each cycle tries to acquire a transaction-level advisory lock.
    Only one worker across all instances polls per cycle. If the
    leader dies, the lock auto-releases and the next worker takes over
    on the very next cycle - no gap.
    """
    _shutdown = shutdown or asyncio.Event()
    logger.info("[poller] Started (interval=%.1fs)", interval)

    while not _shutdown.is_set():
        try:
            count = await _try_poll_with_lock()
            if count == -1:
                logger.debug("[poller] Another worker is polling, skipping")
            elif count > 0:
                logger.info("[poller] Dispatched %d task(s)", count)
            else:
                logger.debug("[poller] No new comments or rebase triggers found")
        except Exception:
            logger.exception("[poller] Poll error")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass

    logger.info("[poller] Stopped")
