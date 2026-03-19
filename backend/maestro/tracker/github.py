"""GitHub Issues tracker adapter."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from maestro.models import Issue
from maestro.tracker.base import TrackerClient

logger = logging.getLogger(__name__)


class GitHubClient(TrackerClient):
    """GitHub Issues tracker adapter using REST API.

    When no repo is specified, fetches issues across all repos
    the token has access to.
    """

    def __init__(
        self,
        token: str,
        repo: str = "",
        endpoint: str = "https://api.github.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._repo = repo  # optional "owner/repo" filter
        self._endpoint = endpoint.rstrip("/")
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

    async def fetch_candidate_issues(self) -> list[Issue]:
        """Fetch open issues from all accessible repos or a specific repo."""
        if self._repo:
            return await self._fetch_repo_issues(self._repo, state="open")
        return await self._fetch_all_issues(state="open")

    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        all_issues: list[Issue] = []
        for state in states:
            gh_state = _map_state_to_github(state)
            if gh_state:
                if self._repo:
                    all_issues.extend(
                        await self._fetch_repo_issues(self._repo, state=gh_state)
                    )
                else:
                    all_issues.extend(await self._fetch_all_issues(state=gh_state))
        return all_issues

    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        """Fetch current state for issues. IDs should be 'owner/repo#number'."""
        result: dict[str, str] = {}
        for issue_id in issue_ids:
            try:
                if "#" in issue_id:
                    repo, number = issue_id.rsplit("#", 1)
                    resp = await self._http.get(f"/repos/{repo}/issues/{number}")
                elif self._repo:
                    resp = await self._http.get(f"/repos/{self._repo}/issues/{issue_id}")
                else:
                    continue
                resp.raise_for_status()
                data = resp.json()
                result[issue_id] = data.get("state", "unknown")
            except Exception:
                logger.warning("Failed to fetch state for issue %s", issue_id)
        return result

    async def fetch_repos(self) -> list[dict[str, Any]]:
        """Fetch all repos accessible to the token."""
        repos: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = await self._http.get(
                "/user/repos",
                params={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                repos.append({
                    "full_name": item["full_name"],
                    "name": item["name"],
                    "owner": item["owner"]["login"],
                    "private": item["private"],
                    "open_issues_count": item.get("open_issues_count", 0),
                    "html_url": item["html_url"],
                })
            if len(items) < 100:
                break
            page += 1
        return repos

    async def _fetch_all_issues(self, state: str = "open") -> list[Issue]:
        """Fetch issues across all repos using the /user/issues endpoint."""
        all_issues: list[Issue] = []
        page = 1
        while True:
            resp = await self._http.get(
                "/user/issues",
                params={
                    "state": state,
                    "filter": "all",
                    "per_page": 50,
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                if "pull_request" in item:
                    continue
                repo = item.get("repository", {}).get("full_name", "")
                all_issues.append(_normalize_issue(item, repo))
            if len(items) < 50:
                break
            page += 1
        return all_issues

    async def _fetch_repo_issues(
        self,
        repo: str,
        state: str = "open",
        per_page: int = 50,
    ) -> list[Issue]:
        """Fetch issues from a specific repo."""
        all_issues: list[Issue] = []
        page = 1
        while True:
            resp = await self._http.get(
                f"/repos/{repo}/issues",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                if "pull_request" in item:
                    continue
                all_issues.append(_normalize_issue(item, repo))
            if len(items) < per_page:
                break
            page += 1
        return all_issues

    async def search_issues(self, query: str) -> list[Issue]:
        """Search issues across accessible repos or within a specific repo."""
        q = f"{query} is:issue"
        if self._repo:
            q += f" repo:{self._repo}"
        resp = await self._http.get(
            "/search/issues",
            params={"q": q, "per_page": 30},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            _normalize_issue(
                item,
                item.get("repository_url", "").replace(f"{self._endpoint}/repos/", ""),
            )
            for item in data.get("items", [])
        ]


def _normalize_issue(item: dict[str, Any], repo: str) -> Issue:
    """Normalize a GitHub issue to our domain model."""
    labels = [label["name"].lower() for label in (item.get("labels") or [])]

    priority = None
    for label in labels:
        if label.startswith("priority:"):
            try:
                priority = int(label.split(":")[1].strip())
            except (ValueError, IndexError):
                pass

    # Use repo-qualified identifier for cross-repo support
    number = item["number"]
    identifier = f"{repo}#{number}" if repo else f"#{number}"

    return Issue(
        id=str(number),
        identifier=identifier,
        title=item["title"],
        description=item.get("body"),
        priority=priority,
        state=item["state"],
        branch_name=None,
        url=item.get("html_url"),
        labels=labels,
        blocked_by=[],
        created_at=_parse_dt(item.get("created_at")),
        updated_at=_parse_dt(item.get("updated_at")),
    )


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _map_state_to_github(state: str) -> str | None:
    """Map generic states to GitHub issue states."""
    s = state.lower()
    if s in ("open", "todo", "in progress", "in_progress"):
        return "open"
    if s in ("closed", "done", "canceled", "cancelled"):
        return "closed"
    return None
