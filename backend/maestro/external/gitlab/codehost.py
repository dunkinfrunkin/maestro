"""GitLab code host — implements CodeHost interface.

Uses GitLab REST API v4 for merge request operations.
Works with both GitLab.com and self-hosted instances.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from maestro.external.base import (
    CICheck,
    CIStatus,
    CodeHost,
    MergeResult,
    PRComment,
    ReviewResult,
)

logger = logging.getLogger(__name__)


class GitLabCodeHost(CodeHost):
    """GitLab merge request operations using REST API v4.

    Args:
        token: Personal access token or project access token
        endpoint: GitLab instance URL (default: https://gitlab.com)
    """

    def __init__(
        self,
        token: str,
        endpoint: str = "https://gitlab.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token
        self._http = httpx.AsyncClient(
            base_url=f"{self._endpoint}/api/v4",
            headers={
                "PRIVATE-TOKEN": token,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout_ms / 1000.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def create_review(
        self,
        repo: str,
        pr_number: int,
        comments: list[dict[str, Any]],
        verdict: str = "COMMENT",
        summary: str = "",
    ) -> ReviewResult:
        """Post review comments on a merge request.

        GitLab doesn't have a single "review" concept like GitHub.
        We post individual discussion notes on the MR diff.
        For APPROVE/REQUEST_CHANGES, we use the MR approvals API.
        """
        project_path = quote(repo, safe="")

        # Post inline comments as diff discussions
        for c in comments:
            try:
                # Get the latest diff version
                versions_resp = await self._http.get(
                    f"/projects/{project_path}/merge_requests/{pr_number}/versions"
                )
                versions_resp.raise_for_status()
                versions = versions_resp.json()
                if not versions:
                    continue

                head_sha = versions[0].get("head_commit_sha", "")
                base_sha = versions[0].get("base_commit_sha", "")

                await self._http.post(
                    f"/projects/{project_path}/merge_requests/{pr_number}/discussions",
                    json={
                        "body": c["body"],
                        "position": {
                            "position_type": "text",
                            "base_sha": base_sha,
                            "head_sha": head_sha,
                            "start_sha": base_sha,
                            "new_path": c["path"],
                            "new_line": c["line"],
                        },
                    },
                )
            except Exception as e:
                logger.warning("Failed to post inline comment on %s: %s", c.get("path"), e)

        # Post summary as a regular note
        if summary:
            await self._http.post(
                f"/projects/{project_path}/merge_requests/{pr_number}/notes",
                json={"body": summary},
            )

        # Handle verdict
        if verdict.upper() == "APPROVE":
            try:
                await self._http.post(
                    f"/projects/{project_path}/merge_requests/{pr_number}/approve"
                )
            except Exception as e:
                logger.warning("Failed to approve MR: %s", e)

        return ReviewResult(status="posted")

    async def reply_to_comment(
        self, repo: str, comment_id: str, body: str
    ) -> None:
        """Reply to a discussion note.

        comment_id should be "discussion_id:note_id" format.
        """
        project_path = quote(repo, safe="")

        # We need the MR IID and discussion ID to reply
        # comment_id format: "{mr_iid}:{discussion_id}"
        parts = comment_id.split(":")
        if len(parts) != 2:
            logger.error("Invalid comment_id format for GitLab: %s (expected 'mr_iid:discussion_id')", comment_id)
            return

        mr_iid, discussion_id = parts
        await self._http.post(
            f"/projects/{project_path}/merge_requests/{mr_iid}/discussions/{discussion_id}/notes",
            json={"body": body},
        )

    async def resolve_thread(self, repo: str, thread_id: str) -> None:
        """Resolve a discussion thread.

        thread_id format: "{mr_iid}:{discussion_id}"
        """
        project_path = quote(repo, safe="")
        parts = thread_id.split(":")
        if len(parts) != 2:
            logger.error("Invalid thread_id format for GitLab: %s", thread_id)
            return

        mr_iid, discussion_id = parts
        await self._http.put(
            f"/projects/{project_path}/merge_requests/{mr_iid}/discussions/{discussion_id}",
            json={"resolved": True},
        )

    async def merge_pr(
        self, repo: str, pr_number: int, strategy: str = "squash"
    ) -> MergeResult:
        project_path = quote(repo, safe="")

        payload: dict[str, Any] = {}
        if strategy == "squash":
            payload["squash"] = True
        elif strategy == "rebase":
            # Rebase first, then merge
            try:
                await self._http.put(
                    f"/projects/{project_path}/merge_requests/{pr_number}/rebase"
                )
            except Exception:
                pass

        try:
            resp = await self._http.put(
                f"/projects/{project_path}/merge_requests/{pr_number}/merge",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return MergeResult(
                status="merged",
                sha=data.get("merge_commit_sha", ""),
            )
        except httpx.HTTPStatusError as e:
            return MergeResult(status="failed", error=e.response.text)

    async def get_ci_status(self, repo: str, pr_number: int) -> CIStatus:
        project_path = quote(repo, safe="")

        # Get pipelines for the MR
        resp = await self._http.get(
            f"/projects/{project_path}/merge_requests/{pr_number}/pipelines"
        )
        resp.raise_for_status()
        pipelines = resp.json()

        if not pipelines:
            return CIStatus(checks=[], all_passed=False)

        # Get jobs from the latest pipeline
        latest_pipeline_id = pipelines[0]["id"]
        jobs_resp = await self._http.get(
            f"/projects/{project_path}/pipelines/{latest_pipeline_id}/jobs",
            params={"per_page": 100},
        )
        jobs_resp.raise_for_status()
        jobs = jobs_resp.json()

        checks = []
        all_passed = True
        for job in jobs:
            status = _map_gitlab_job_status(job.get("status", ""))
            checks.append(CICheck(
                name=job.get("name", ""),
                status=status,
                url=job.get("web_url", ""),
            ))
            if status != "passed":
                all_passed = False

        return CIStatus(checks=checks, all_passed=all_passed and len(checks) > 0)

    async def get_pr_comments(
        self, repo: str, pr_number: int
    ) -> list[PRComment]:
        project_path = quote(repo, safe="")
        comments: list[PRComment] = []

        # Get all discussions (threads) on the MR
        page = 1
        while True:
            resp = await self._http.get(
                f"/projects/{project_path}/merge_requests/{pr_number}/discussions",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            discussions = resp.json()
            if not discussions:
                break

            for discussion in discussions:
                notes = discussion.get("notes", [])
                if not notes:
                    continue
                first_note = notes[0]

                # Only include diff notes (inline comments)
                position = first_note.get("position")
                path = ""
                line = 0
                if position:
                    path = position.get("new_path", "")
                    line = position.get("new_line") or 0

                comments.append(PRComment(
                    id=f"{pr_number}:{discussion['id']}",
                    body=first_note.get("body", ""),
                    path=path,
                    line=line,
                    user=first_note.get("author", {}).get("username", ""),
                    reply_count=len(notes) - 1,
                ))

            if len(discussions) < 100:
                break
            page += 1

        return comments


def _map_gitlab_job_status(status: str) -> str:
    mapping = {
        "success": "passed",
        "failed": "failed",
        "canceled": "failed",
        "skipped": "passed",
        "running": "running",
        "pending": "pending",
        "created": "pending",
        "manual": "pending",
    }
    return mapping.get(status, "unknown")
