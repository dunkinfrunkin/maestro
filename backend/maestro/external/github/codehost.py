"""GitHub code host — implements CodeHost interface using REST + GraphQL."""

from __future__ import annotations

import logging
from typing import Any

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


class GitHubCodeHost(CodeHost):
    """GitHub PR operations using REST API and GraphQL.

    Uses httpx with a stored token — no dependency on `gh` CLI.
    """

    def __init__(
        self,
        token: str,
        endpoint: str = "https://api.github.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token
        self._http = httpx.AsyncClient(
            base_url=self._endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
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
        event_map = {
            "APPROVE": "APPROVE",
            "REQUEST_CHANGES": "REQUEST_CHANGES",
            "COMMENT": "COMMENT",
        }
        event = event_map.get(verdict.upper(), "COMMENT")

        review_comments = []
        for c in comments:
            review_comments.append({
                "path": c["path"],
                "line": c["line"],
                "side": "RIGHT",
                "body": c["body"],
            })

        payload: dict[str, Any] = {
            "body": summary or f"Review: {verdict}",
            "event": event,
        }
        if review_comments:
            payload["comments"] = review_comments

        try:
            resp = await self._http.post(
                f"/repos/{repo}/pulls/{pr_number}/reviews",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return ReviewResult(
                status="posted",
                review_id=str(data.get("id", "")),
                html_url=data.get("html_url", ""),
            )
        except httpx.HTTPStatusError as e:
            error = e.response.text
            logger.error("Failed to post review: %s", error)

            # Fallback: post as a plain review without inline comments
            # (happens if lines aren't part of the diff)
            if review_comments:
                fallback_body = (summary or "") + "\n\n"
                for c in comments:
                    fallback_body += f"**{c['path']}:{c['line']}** — {c['body']}\n\n"
                try:
                    resp2 = await self._http.post(
                        f"/repos/{repo}/pulls/{pr_number}/reviews",
                        json={"body": fallback_body, "event": event},
                    )
                    resp2.raise_for_status()
                    return ReviewResult(status="posted", error="fallback: no inline")
                except Exception:
                    pass

            return ReviewResult(status="failed", error=error)

    async def reply_to_comment(
        self, repo: str, comment_id: str, body: str
    ) -> None:
        resp = await self._http.post(
            f"/repos/{repo}/pulls/comments/{comment_id}/replies",
            json={"body": body},
        )
        resp.raise_for_status()

    async def resolve_thread(self, repo: str, thread_id: str) -> None:
        """Resolve a review thread via GitHub GraphQL API."""
        query = """
        mutation ResolveThread($threadId: ID!) {
          resolveReviewThread(input: {threadId: $threadId}) {
            thread { isResolved }
          }
        }
        """
        resp = await self._http.post(
            f"{self._endpoint}/graphql"
            if not self._endpoint.endswith("/graphql")
            else self._endpoint,
            json={"query": query, "variables": {"threadId": thread_id}},
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            logger.error("GraphQL error resolving thread: %s", data["errors"])

    async def merge_pr(
        self, repo: str, pr_number: int, strategy: str = "squash"
    ) -> MergeResult:
        merge_method_map = {
            "squash": "squash",
            "merge": "merge",
            "rebase": "rebase",
        }
        merge_method = merge_method_map.get(strategy, "squash")

        try:
            resp = await self._http.put(
                f"/repos/{repo}/pulls/{pr_number}/merge",
                json={"merge_method": merge_method},
            )
            resp.raise_for_status()
            data = resp.json()
            return MergeResult(
                status="merged",
                sha=data.get("sha", ""),
            )
        except httpx.HTTPStatusError as e:
            return MergeResult(status="failed", error=e.response.text)

    async def get_ci_status(self, repo: str, pr_number: int) -> CIStatus:
        # First get the PR to find the head SHA
        pr_resp = await self._http.get(f"/repos/{repo}/pulls/{pr_number}")
        pr_resp.raise_for_status()
        head_sha = pr_resp.json()["head"]["sha"]

        # Get check runs for the commit
        resp = await self._http.get(
            f"/repos/{repo}/commits/{head_sha}/check-runs",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        data = resp.json()

        checks = []
        all_passed = True
        for run in data.get("check_runs", []):
            status = _map_check_status(run.get("status"), run.get("conclusion"))
            checks.append(CICheck(
                name=run.get("name", ""),
                status=status,
                url=run.get("html_url", ""),
            ))
            if status != "passed":
                all_passed = False

        return CIStatus(checks=checks, all_passed=all_passed and len(checks) > 0)

    async def get_pr_comments(
        self, repo: str, pr_number: int
    ) -> list[PRComment]:
        comments: list[PRComment] = []
        page = 1
        while True:
            resp = await self._http.get(
                f"/repos/{repo}/pulls/{pr_number}/comments",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                comments.append(PRComment(
                    id=str(item["id"]),
                    body=item.get("body", ""),
                    path=item.get("path", ""),
                    line=item.get("line") or item.get("original_line") or 0,
                    user=item.get("user", {}).get("login", ""),
                ))
            if len(items) < 100:
                break
            page += 1
        return comments


def _map_check_status(status: str | None, conclusion: str | None) -> str:
    if status == "completed":
        if conclusion == "success":
            return "passed"
        if conclusion in ("failure", "timed_out", "action_required"):
            return "failed"
        return conclusion or "unknown"
    if status in ("queued", "in_progress"):
        return "running"
    return "pending"
