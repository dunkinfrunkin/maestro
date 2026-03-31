"""GitHub Issues tracker — implements IssueTracker interface."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from maestro.external.base import IssueTracker
from maestro.models import Issue

logger = logging.getLogger(__name__)


class GitHubIssueTracker(IssueTracker):
    """GitHub Issues tracker using REST API.

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

    async def fetch_candidate_issues(self, max_results: int = 100) -> list[Issue]:
        if self._repo:
            return await self._fetch_repo_issues(self._repo, state="open", max_results=max_results)
        return await self._fetch_all_issues(state="open", max_results=max_results)

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

    async def fetch_repos(self, search: str = "") -> list[dict[str, Any]]:
        """Fetch repos accessible to the token, optionally filtered by search."""
        if search:
            return await self._search_repos(search)
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
                repos.append(_normalize_repo(item))
            if len(items) < 100:
                break
            page += 1
        return repos

    async def _search_repos(self, query: str) -> list[dict[str, Any]]:
        """Search repos using GitHub's search API."""
        resp = await self._http.get(
            "/search/repositories",
            params={"q": query, "per_page": 30, "sort": "updated"},
        )
        resp.raise_for_status()
        data = resp.json()
        return [_normalize_repo(item) for item in data.get("items", [])]

    async def search_issues(self, query: str) -> list[Issue]:
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

    async def _fetch_all_issues(self, state: str = "open", max_results: int = 100) -> list[Issue]:
        all_issues: list[Issue] = []
        page = 1
        per_page = min(50, max_results)
        while True:
            resp = await self._http.get(
                "/user/issues",
                params={
                    "state": state,
                    "filter": "all",
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
                repo = item.get("repository", {}).get("full_name", "")
                all_issues.append(_normalize_issue(item, repo))
            if len(all_issues) >= max_results or len(items) < per_page:
                break
            page += 1
        return all_issues[:max_results]

    async def _fetch_repo_issues(
        self,
        repo: str,
        state: str = "open",
        max_results: int = 100,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        page = 1
        per_page = min(50, max_results)
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
            if len(all_issues) >= max_results or len(items) < per_page:
                break
            page += 1
        return all_issues[:max_results]


def _normalize_repo(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "full_name": item["full_name"],
        "name": item["name"],
        "owner": item["owner"]["login"],
        "private": item["private"],
        "open_issues_count": item.get("open_issues_count", 0),
        "html_url": item["html_url"],
    }


def _normalize_issue(item: dict[str, Any], repo: str) -> Issue:
    labels = [label["name"].lower() for label in (item.get("labels") or [])]

    priority = None
    for label in labels:
        if label.startswith("priority:"):
            try:
                priority = int(label.split(":")[1].strip())
            except (ValueError, IndexError):
                pass

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
    s = state.lower()
    if s in ("open", "todo", "in progress", "in_progress"):
        return "open"
    if s in ("closed", "done", "canceled", "cancelled"):
        return "closed"
    return None
