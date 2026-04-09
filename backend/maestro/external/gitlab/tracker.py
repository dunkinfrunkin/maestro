"""GitLab Issues tracker — implements IssueTracker interface.

Uses GitLab REST API v4. Works with both GitLab.com and self-hosted.
Authenticates via personal access token (PRIVATE-TOKEN header).

Supports:
- All issues the token has access to (no group specified)
- Group-scoped issues (e.g., "engineering/ai")
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from maestro.external.base import IssueTracker
from maestro.models import Issue

logger = logging.getLogger(__name__)


class GitLabIssueTracker(IssueTracker):
    """GitLab issue tracker using REST API v4.

    Args:
        token: Personal access token (needs api or read_api scope)
        group: Optional group path (e.g., "engineering/ai"). If empty,
               fetches issues across all accessible projects.
        endpoint: GitLab instance URL (default: https://gitlab.com)
    """

    def __init__(
        self,
        token: str,
        group: str = "",
        endpoint: str = "https://gitlab.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._group = group
        self._group_path = quote(group, safe="") if group else ""
        self._http = httpx.AsyncClient(
            base_url=f"{self._endpoint}/api/v4",
            headers={
                "PRIVATE-TOKEN": token,
                "Accept": "application/json",
            },
            timeout=timeout_ms / 1000.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def fetch_projects(self, search: str = "") -> list[dict[str, Any]]:
        """Fetch projects (repos) accessible to the token, optionally filtered."""
        projects: list[dict[str, Any]] = []
        page = 1
        base = f"/groups/{self._group_path}/projects" if self._group_path else "/projects"
        params: dict[str, Any] = {
            "per_page": 50,
            "page": page,
            "order_by": "last_activity_at",
            "sort": "desc",
            "membership": "true",
        }
        if search:
            params["search"] = search
        while True:
            params["page"] = page
            resp = await self._http.get(base, params=params)
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                projects.append({
                    "full_name": item.get("path_with_namespace", ""),
                    "name": item.get("name", ""),
                    "owner": item.get("namespace", {}).get("full_path", ""),
                    "private": item.get("visibility") == "private",
                    "open_issues_count": item.get("open_issues_count", 0),
                    "html_url": item.get("web_url", ""),
                })
            if len(items) < 50:
                break
            page += 1
        return projects

    async def fetch_candidate_issues(self, max_results: int = 100, user_email: str = "") -> list[Issue]:
        return await self._fetch_issues(state="opened", max_results=max_results)

    async def fetch_issues_by_states(self, states: list[str], user_email: str = "") -> list[Issue]:
        all_issues: list[Issue] = []
        for state in states:
            gl_state = _map_state_to_gitlab(state)
            if gl_state:
                all_issues.extend(await self._fetch_issues(state=gl_state))
        return all_issues

    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for issue_id in issue_ids:
            try:
                # issue_id format: "group/project#iid" or just "iid"
                if "#" in issue_id:
                    project_path, iid = issue_id.rsplit("#", 1)
                    encoded = quote(project_path, safe="")
                    resp = await self._http.get(f"/projects/{encoded}/issues/{iid}")
                else:
                    # Can't look up by IID without a project — skip
                    continue
                resp.raise_for_status()
                data = resp.json()
                result[issue_id] = data.get("state", "unknown")
            except Exception:
                logger.warning("Failed to fetch state for GitLab issue %s", issue_id)
        return result

    async def search_issues(self, query: str) -> list[Issue]:
        base = self._issues_base_url()
        resp = await self._http.get(
            base,
            params={"search": query, "per_page": 30, "order_by": "created_at", "sort": "desc"},
        )
        resp.raise_for_status()
        return [_normalize_issue(item, self._endpoint) for item in resp.json()]

    async def _fetch_issues(self, state: str = "opened", max_results: int = 100) -> list[Issue]:
        all_issues: list[Issue] = []
        base = self._issues_base_url()
        page = 1
        per_page = min(50, max_results)
        while True:
            resp = await self._http.get(
                base,
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "order_by": "created_at",
                    "sort": "desc",
                },
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            for item in items:
                all_issues.append(_normalize_issue(item, self._endpoint))
            if len(all_issues) >= max_results or len(items) < per_page:
                break
            page += 1
        return all_issues[:max_results]

    def _issues_base_url(self) -> str:
        """Return the right issues endpoint based on config."""
        if self._group_path:
            return f"/groups/{self._group_path}/issues"
        return "/issues"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_issue(item: dict[str, Any], endpoint: str) -> Issue:
    labels = [label.lower() for label in (item.get("labels") or [])]

    # Priority from labels (e.g., "priority::1")
    priority = None
    for label in labels:
        if label.startswith("priority::"):
            try:
                priority = int(label.split("::")[1])
            except (ValueError, IndexError):
                pass

    blocked_by: list[str] = []

    iid = item.get("iid", "")
    # Build identifier from project path + iid
    refs = item.get("references", {})
    identifier = refs.get("full", "") or f"#{iid}"

    return Issue(
        id=str(item.get("id", "")),
        identifier=identifier,
        title=item.get("title", ""),
        description=item.get("description"),
        priority=priority,
        state=item.get("state", "unknown"),
        branch_name=None,
        url=item.get("web_url"),
        labels=labels,
        blocked_by=blocked_by,
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


def _map_state_to_gitlab(state: str) -> str | None:
    s = state.lower()
    if s in ("open", "opened", "todo", "in progress", "in_progress", "reopened"):
        return "opened"
    if s in ("closed", "done", "resolved", "cancelled", "canceled"):
        return "closed"
    return None
