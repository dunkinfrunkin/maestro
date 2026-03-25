"""GitLab Issues tracker — implements IssueTracker interface.

Uses GitLab REST API v4. Works with both GitLab.com and self-hosted.
Authenticates via personal access token (PRIVATE-TOKEN header).
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
        token: Personal access token or project access token
        project_id: Numeric project ID or URL-encoded path ("group/project")
        endpoint: GitLab instance URL (default: https://gitlab.com)
    """

    def __init__(
        self,
        token: str,
        project_id: str,
        endpoint: str = "https://gitlab.com",
        timeout_ms: int = 30000,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._project_id = project_id
        self._project_path = quote(project_id, safe="") if not project_id.isdigit() else project_id
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

    async def fetch_candidate_issues(self) -> list[Issue]:
        return await self._fetch_issues(state="opened")

    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        all_issues: list[Issue] = []
        for state in states:
            gl_state = _map_state_to_gitlab(state)
            if gl_state:
                all_issues.extend(await self._fetch_issues(state=gl_state))
        return all_issues

    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for iid in issue_ids:
            try:
                resp = await self._http.get(
                    f"/projects/{self._project_path}/issues/{iid}"
                )
                resp.raise_for_status()
                data = resp.json()
                result[iid] = data.get("state", "unknown")
            except Exception:
                logger.warning("Failed to fetch state for GitLab issue %s", iid)
        return result

    async def search_issues(self, query: str) -> list[Issue]:
        resp = await self._http.get(
            f"/projects/{self._project_path}/issues",
            params={"search": query, "per_page": 30, "order_by": "created_at", "sort": "desc"},
        )
        resp.raise_for_status()
        return [_normalize_issue(item, self._endpoint, self._project_id) for item in resp.json()]

    async def _fetch_issues(self, state: str = "opened", per_page: int = 50) -> list[Issue]:
        all_issues: list[Issue] = []
        page = 1
        while True:
            resp = await self._http.get(
                f"/projects/{self._project_path}/issues",
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
                all_issues.append(_normalize_issue(item, self._endpoint, self._project_id))
            if len(items) < per_page:
                break
            page += 1
        return all_issues


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_issue(item: dict[str, Any], endpoint: str, project_id: str) -> Issue:
    labels = [label.lower() for label in (item.get("labels") or [])]

    # Priority from labels (e.g., "priority::1")
    priority = None
    for label in labels:
        if label.startswith("priority::"):
            try:
                priority = int(label.split("::")[1])
            except (ValueError, IndexError):
                pass

    # Blocked by — GitLab uses "blocked_by" in issue links (not in basic issue response)
    blocked_by: list[str] = []

    iid = item.get("iid", "")
    identifier = f"{project_id}#{iid}"

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
