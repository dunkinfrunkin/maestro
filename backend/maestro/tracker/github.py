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
    """GitHub Issues tracker adapter using REST API."""

    def __init__(
        self,
        token: str,
        repo: str,
        endpoint: str = "https://api.github.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._repo = repo  # "owner/repo"
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
        """Fetch open issues (candidates for work)."""
        return await self._fetch_issues(state="open")

    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        """Fetch issues by state. GitHub states: 'open', 'closed', 'all'."""
        all_issues: list[Issue] = []
        for state in states:
            gh_state = _map_state_to_github(state)
            if gh_state:
                all_issues.extend(await self._fetch_issues(state=gh_state))
        return all_issues

    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        """Fetch current state for issues by their number."""
        result: dict[str, str] = {}
        for issue_id in issue_ids:
            try:
                resp = await self._http.get(f"/repos/{self._repo}/issues/{issue_id}")
                resp.raise_for_status()
                data = resp.json()
                result[issue_id] = data.get("state", "unknown")
            except Exception:
                logger.warning("Failed to fetch state for issue %s", issue_id)
        return result

    async def _fetch_issues(
        self,
        state: str = "open",
        per_page: int = 50,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        page = 1
        while True:
            resp = await self._http.get(
                f"/repos/{self._repo}/issues",
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
                # Skip pull requests (GitHub returns them in /issues)
                if "pull_request" in item:
                    continue
                all_issues.append(_normalize_issue(item, self._repo))
            if len(items) < per_page:
                break
            page += 1
        return all_issues

    async def search_issues(self, query: str) -> list[Issue]:
        """Search issues in the repo."""
        resp = await self._http.get(
            "/search/issues",
            params={"q": f"{query} repo:{self._repo} is:issue", "per_page": 30},
        )
        resp.raise_for_status()
        data = resp.json()
        return [_normalize_issue(item, self._repo) for item in data.get("items", [])]


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

    return Issue(
        id=str(item["number"]),
        identifier=f"#{item['number']}",
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
