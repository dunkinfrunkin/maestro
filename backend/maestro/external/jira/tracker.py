"""Jira Cloud/Server tracker — implements IssueTracker interface.

Uses the Jira REST API v3 (Cloud) or v2 (Server/Data Center).
Authenticates via API token (Cloud: email + token, Server: PAT).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from maestro.external.base import IssueTracker
from maestro.models import Issue

logger = logging.getLogger(__name__)

# Jira Cloud uses basic auth (email:token). Server uses Bearer PAT.
# We detect based on whether an email is provided.


class JiraIssueTracker(IssueTracker):
    """Jira issue tracker using REST API.

    Works with both Jira Cloud and Jira Server/Data Center.

    Cloud example:
        JiraIssueTracker(
            base_url="https://mycompany.atlassian.net",
            email="user@company.com",
            api_token="ATATT...",
            project_key="ENG",
        )

    Server example:
        JiraIssueTracker(
            base_url="https://jira.internal.company.com",
            api_token="NDE...",  # PAT
            project_key="ENG",
        )
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        project_key: str,
        email: str = "",
        assignee_email: str = "",
        active_statuses: list[str] | None = None,
        terminal_statuses: list[str] | None = None,
        api_version: str = "3",
        timeout_ms: int = 30000,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._assignee_email = assignee_email
        self._assignee_account_id: str | None = None  # resolved lazily
        # Support comma-separated project keys: "ENG,PLATFORM,INFRA"
        self._project_keys = [k.strip() for k in project_key.split(",") if k.strip()]
        self._active_statuses = active_statuses or [
            "To Do",
            "In Progress",
            "Open",
            "Reopened",
        ]
        self._terminal_statuses = terminal_statuses or [
            "Done",
            "Closed",
            "Resolved",
            "Cancelled",
        ]
        self._api_version = api_version
        self._api_base = f"{self._base_url}/rest/api/{api_version}"

        # Cloud: basic auth with email:token
        # Server: Bearer token (PAT)
        if email:
            import base64

            creds = base64.b64encode(f"{email}:{api_token}".encode()).decode()
            auth_header = f"Basic {creds}"
        else:
            auth_header = f"Bearer {api_token}"

        self._http = httpx.AsyncClient(
            headers={
                "Authorization": auth_header,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout_ms / 1000.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    def _project_clause(self) -> str:
        """Build JQL project clause — supports multiple keys."""
        if not self._project_keys:
            return ""
        if len(self._project_keys) == 1:
            return f"project = {self._project_keys[0]}"
        keys = ", ".join(self._project_keys)
        return f"project in ({keys})"

    async def _resolve_assignee_account_id(self) -> str | None:
        """Resolve the assignee email to a Jira account ID (cached)."""
        if self._assignee_account_id is not None:
            return self._assignee_account_id
        if not self._assignee_email:
            return None
        try:
            resp = await self._http.get(
                f"{self._api_base}/user/search",
                params={"query": self._assignee_email, "maxResults": 1},
            )
            resp.raise_for_status()
            users = resp.json()
            if users:
                self._assignee_account_id = users[0].get("accountId", "")
                return self._assignee_account_id
        except Exception:
            logger.warning("Failed to resolve Jira account for %s", self._assignee_email)
        return None

    async def _base_clauses(self) -> list[str]:
        """Collect non-empty base JQL clauses (project + assignee)."""
        clauses = []
        project = self._project_clause()
        if project:
            clauses.append(project)
        account_id = await self._resolve_assignee_account_id()
        if account_id:
            clauses.append(f'assignee = "{account_id}"')
        return clauses

    async def fetch_candidate_issues(self) -> list[Issue]:
        status_clause = _jql_status_in(self._active_statuses)
        clauses = await self._base_clauses()
        clauses.append(status_clause)
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql)

    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        if not states:
            return []
        status_clause = _jql_status_in(states)
        clauses = await self._base_clauses()
        clauses.append(status_clause)
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql)

    async def fetch_issue_states_by_ids(
        self, issue_ids: list[str]
    ) -> dict[str, str]:
        if not issue_ids:
            return {}

        result: dict[str, str] = {}
        # Jira supports querying by key (ENG-123) or by ID
        keys = [k for k in issue_ids if "-" in k]
        ids = [k for k in issue_ids if "-" not in k]

        if keys:
            key_clause = ", ".join(f'"{k}"' for k in keys)
            jql = f"key in ({key_clause})"
            issues = await self._search(jql, fields=["status"])
            for issue in issues:
                result[issue.identifier] = issue.state

        if ids:
            id_clause = ", ".join(ids)
            jql = f"id in ({id_clause})"
            issues = await self._search(jql, fields=["status"])
            for issue in issues:
                result[issue.id] = issue.state

        return result

    async def search_issues(self, query: str) -> list[Issue]:
        clauses = await self._base_clauses()
        clauses.append(f'text ~ "{_escape_jql(query)}"')
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql, max_results=30)

    async def _search(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int = 50,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        start_at = 0

        default_fields = [
            "summary",
            "description",
            "status",
            "priority",
            "labels",
            "created",
            "updated",
            "issuetype",
            "issuelinks",
        ]

        while True:
            resp = await self._http.post(
                f"{self._api_base}/search",
                json={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": fields or default_fields,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("issues", []):
                all_issues.append(_normalize_issue(item, self._base_url))

            total = data.get("total", 0)
            start_at += len(data.get("issues", []))
            if start_at >= total or start_at >= max_results:
                break

        return all_issues


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_issue(item: dict[str, Any], base_url: str) -> Issue:
    fields = item.get("fields", {})

    # Labels
    labels = [label.lower() for label in (fields.get("labels") or [])]

    # Priority — Jira uses names like "High", "Medium", "Low"
    priority = None
    priority_field = fields.get("priority")
    if priority_field and isinstance(priority_field, dict):
        priority_name = priority_field.get("name", "").lower()
        priority_map = {
            "highest": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "lowest": 5,
        }
        priority = priority_map.get(priority_name)

    # Status
    status = fields.get("status", {})
    state = status.get("name", "Unknown") if isinstance(status, dict) else "Unknown"

    # Blocked by (from issue links)
    blocked_by: list[str] = []
    for link in fields.get("issuelinks") or []:
        link_type = link.get("type", {}).get("name", "")
        if link_type.lower() in ("blocks", "is blocked by"):
            inward = link.get("inwardIssue")
            if inward:
                blocked_by.append(inward.get("key", ""))

    # Description — v3 uses ADF (Atlassian Document Format), v2 uses plaintext
    description = fields.get("description")
    if isinstance(description, dict):
        # ADF: extract text content
        description = _extract_adf_text(description)

    key = item.get("key", "")

    return Issue(
        id=str(item.get("id", "")),
        identifier=key,
        title=fields.get("summary", ""),
        description=description,
        priority=priority,
        state=state,
        branch_name=None,
        url=f"{base_url}/browse/{key}" if key else None,
        labels=labels,
        blocked_by=blocked_by,
        created_at=_parse_dt(fields.get("created")),
        updated_at=_parse_dt(fields.get("updated")),
    )


def _extract_adf_text(adf: dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format."""
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "text":
                parts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf)
    return "\n".join(parts) if parts else ""


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _jql_status_in(statuses: list[str]) -> str:
    """Build a JQL status IN clause."""
    quoted = ", ".join(f'"{s}"' for s in statuses)
    return f"status in ({quoted})"


def _escape_jql(text: str) -> str:
    """Escape special JQL characters in a search string."""
    special = r'+-&|!(){}[]^"~*?:\\'
    result = []
    for ch in text:
        if ch in special:
            result.append(f"\\{ch}")
        else:
            result.append(ch)
    return "".join(result)
