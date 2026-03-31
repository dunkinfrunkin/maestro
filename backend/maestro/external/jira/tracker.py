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

    def _base_clauses(self) -> list[str]:
        """Collect non-empty base JQL clauses (project + assignee).

        Uses currentUser() for assignee filtering — this resolves to whoever
        owns the API token, which is the correct behavior since each user
        connects with their own Jira credentials.
        """
        clauses = []
        project = self._project_clause()
        if project:
            clauses.append(project)
        if self._assignee_email:
            clauses.append("assignee = currentUser()")
        return clauses

    async def fetch_candidate_issues(self, max_results: int = 100) -> list[Issue]:
        status_clause = _jql_status_in(self._active_statuses)
        clauses = self._base_clauses()
        clauses.append(status_clause)
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql, max_results=max_results)

    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        if not states:
            return []
        status_clause = _jql_status_in(states)
        clauses = self._base_clauses()
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
        clauses = self._base_clauses()
        clauses.append(f'text ~ "{_escape_jql(query)}"')
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql, max_results=30)

    async def _search(
        self,
        jql: str,
        fields: list[str] | None = None,
        max_results: int = 100,
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        start_at = 0
        per_page = min(50, max_results)

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
            # Jira Cloud deprecated POST /search — use GET /search/jql
            resp = await self._http.get(
                f"{self._api_base}/search/jql",
                params={
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": per_page,
                    "fields": ",".join(fields or default_fields),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("issues", []):
                all_issues.append(_normalize_issue(item, self._base_url))

            total = data.get("total", 0)
            start_at += len(data.get("issues", []))
            if start_at >= total or len(all_issues) >= max_results:
                break

        return all_issues[:max_results]


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
    """Convert Atlassian Document Format to Markdown."""
    return _adf_node_to_md(adf).strip()


def _adf_node_to_md(node: Any, list_depth: int = 0) -> str:
    """Recursively convert an ADF node tree into Markdown."""
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")
    content = node.get("content", [])

    # --- Block nodes ---
    if node_type == "doc":
        return _adf_children(content, list_depth)

    if node_type == "paragraph":
        text = _adf_inline(content)
        return f"{text}\n\n"

    if node_type in ("heading",):
        level = node.get("attrs", {}).get("level", 1)
        text = _adf_inline(content)
        return f"{'#' * level} {text}\n\n"

    if node_type == "bulletList":
        items = ""
        for child in content:
            items += _adf_node_to_md(child, list_depth)
        return items + "\n"

    if node_type == "orderedList":
        items = ""
        for i, child in enumerate(content, 1):
            items += _adf_node_to_md(child, list_depth)
        return items + "\n"

    if node_type == "listItem":
        indent = "  " * list_depth
        parts = []
        for child in content:
            if child.get("type") in ("bulletList", "orderedList"):
                parts.append(_adf_node_to_md(child, list_depth + 1))
            else:
                text = _adf_inline(child.get("content", []))
                parts.append(f"{indent}- {text}\n")
        return "".join(parts)

    if node_type == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        text = _adf_inline(content)
        return f"```{lang}\n{text}\n```\n\n"

    if node_type == "blockquote":
        inner = _adf_children(content, list_depth).strip()
        quoted = "\n".join(f"> {line}" for line in inner.split("\n"))
        return f"{quoted}\n\n"

    if node_type == "rule":
        return "---\n\n"

    if node_type == "table":
        return _adf_table(content)

    if node_type == "mediaSingle" or node_type == "media":
        return ""

    # Fallback: recurse into children
    return _adf_children(content, list_depth)


def _adf_children(content: list[Any], list_depth: int = 0) -> str:
    return "".join(_adf_node_to_md(child, list_depth) for child in content)


def _adf_inline(content: list[Any]) -> str:
    """Convert inline ADF nodes to Markdown text."""
    parts: list[str] = []
    for node in content:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type", "")
        if node_type == "text":
            text = node.get("text", "")
            marks = node.get("marks", [])
            for mark in marks:
                mt = mark.get("type", "")
                if mt == "strong":
                    text = f"**{text}**"
                elif mt == "em":
                    text = f"*{text}*"
                elif mt == "code":
                    text = f"`{text}`"
                elif mt == "strike":
                    text = f"~~{text}~~"
                elif mt == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    text = f"[{text}]({href})"
            parts.append(text)
        elif node_type == "hardBreak":
            parts.append("\n")
        elif node_type == "mention":
            parts.append(f"@{node.get('attrs', {}).get('text', '')}")
        elif node_type == "emoji":
            parts.append(node.get("attrs", {}).get("shortName", ""))
        elif node_type == "inlineCard":
            url = node.get("attrs", {}).get("url", "")
            parts.append(f"[{url}]({url})" if url else "")
        else:
            # Recurse for unknown inline types
            parts.append(_adf_inline(node.get("content", [])))
    return "".join(parts)


def _adf_table(content: list[Any]) -> str:
    """Convert ADF table to Markdown table."""
    rows: list[list[str]] = []
    for row_node in content:
        if row_node.get("type") != "tableRow":
            continue
        cells = []
        for cell in row_node.get("content", []):
            text = _adf_children(cell.get("content", [])).strip().replace("\n", " ")
            cells.append(text)
        rows.append(cells)

    if not rows:
        return ""

    # Build markdown table
    lines = []
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for row in rows[1:]:
        # Pad row to match header width
        while len(row) < len(rows[0]):
            row.append("")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n\n"


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
