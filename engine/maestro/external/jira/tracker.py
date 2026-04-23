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

    def _base_clauses(self, user_email: str = "") -> list[str]:
        """Collect non-empty base JQL clauses (project + assignee).

        If user_email is provided, filters by that user's assignments.
        Otherwise falls back to assignee_email from the connection config.
        """
        clauses = []
        project = self._project_clause()
        if project:
            clauses.append(project)
        email = user_email or self._assignee_email
        if email:
            clauses.append(f'assignee = "{_escape_jql(email)}"')
        return clauses

    async def fetch_candidate_issues(self, max_results: int = 100, user_email: str = "") -> list[Issue]:
        status_clause = _jql_status_in(self._active_statuses)
        clauses = self._base_clauses(user_email)
        clauses.append(status_clause)
        jql = " AND ".join(clauses) + " ORDER BY created DESC"
        return await self._search(jql, max_results=max_results)

    async def fetch_issues_by_states(self, states: list[str], user_email: str = "") -> list[Issue]:
        if not states:
            return []
        status_clause = _jql_status_in(states)
        clauses = self._base_clauses(user_email)
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

    async def update_issue(self, issue_id: str, description: str) -> None:
        """Update a JIRA ticket's description."""
        if self._api_version == "3":
            body = {"fields": {"description": _md_to_adf(description)}}
        else:
            body = {"fields": {"description": description}}
        resp = await self._http.put(f"{self._api_base}/issue/{issue_id}", json=body)
        resp.raise_for_status()

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


def _md_to_adf(text: str) -> dict[str, Any]:
    """Convert markdown to Atlassian Document Format (ADF).

    Handles headings, bullet/ordered/task lists, code blocks, inline
    bold/italic/code/links/strikethrough, and horizontal rules.
    """
    import re as _re

    nodes: list[dict[str, Any]] = []
    lines = text.split("\n")
    i = 0
    _id = [0]

    def _next_id() -> str:
        _id[0] += 1
        return str(_id[0])

    def _inline(src: str) -> list[dict[str, Any]]:
        """Parse inline markdown into ADF text nodes with marks."""
        result: list[dict[str, Any]] = []
        pat = _re.compile(
            r"(?P<code>`[^`]+`)"
            r"|(?P<bold_italic>\*{3}(?P<bi>.+?)\*{3})"
            r"|(?P<bold>\*{2}(?P<b>.+?)\*{2})"
            r"|(?P<bold2>__(?P<b2>.+?)__)"
            r"|(?P<italic>\*(?P<it>.+?)\*)"
            r"|(?P<italic2>_(?P<it2>.+?)_)"
            r"|(?P<strike>~~(?P<s>.+?)~~)"
            r"|\[(?P<lt>[^\]]+)\]\((?P<lh>[^)]+)\)"
        )
        last = 0
        for m in pat.finditer(src):
            if m.start() > last:
                result.append({"type": "text", "text": src[last:m.start()]})
            if m.group("code"):
                result.append({"type": "text", "text": m.group("code")[1:-1], "marks": [{"type": "code"}]})
            elif m.group("bold_italic"):
                result.append({"type": "text", "text": m.group("bi"), "marks": [{"type": "strong"}, {"type": "em"}]})
            elif m.group("bold"):
                result.append({"type": "text", "text": m.group("b"), "marks": [{"type": "strong"}]})
            elif m.group("bold2"):
                result.append({"type": "text", "text": m.group("b2"), "marks": [{"type": "strong"}]})
            elif m.group("italic"):
                result.append({"type": "text", "text": m.group("it"), "marks": [{"type": "em"}]})
            elif m.group("italic2"):
                result.append({"type": "text", "text": m.group("it2"), "marks": [{"type": "em"}]})
            elif m.group("strike"):
                result.append({"type": "text", "text": m.group("s"), "marks": [{"type": "strike"}]})
            elif m.group("lt"):
                result.append({"type": "text", "text": m.group("lt"), "marks": [{"type": "link", "attrs": {"href": m.group("lh")}}]})
            last = m.end()
        if last < len(src):
            result.append({"type": "text", "text": src[last:]})
        return result or [{"type": "text", "text": src}]

    _IS_TASK   = _re.compile(r"^[-*]\s+\[[ xX]\]")
    _IS_BULLET = _re.compile(r"^[-*]\s+")
    _IS_ORDERED = _re.compile(r"^\d+[.)]\s+")
    _IS_HEADING = _re.compile(r"^(#{1,6})\s+(.*)")
    _IS_HR     = _re.compile(r"^(?:[-*_]){3,}\s*$")
    _IS_BLOCK  = _re.compile(r"^(?:#{1,6}\s|```|[-*]\s|\d+[.)]\s|(?:[-*_]){3,}\s*$)")

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            nodes.append({"type": "codeBlock", "attrs": {"language": lang}, "content": [{"type": "text", "text": "\n".join(code)}]})
            continue

        # Heading
        m = _IS_HEADING.match(line)
        if m:
            nodes.append({"type": "heading", "attrs": {"level": len(m.group(1))}, "content": _inline(m.group(2).strip())})
            i += 1
            continue

        # Horizontal rule
        if _IS_HR.match(line):
            nodes.append({"type": "rule"})
            i += 1
            continue

        # Task list
        if _IS_TASK.match(line):
            items: list[dict[str, Any]] = []
            list_id = _next_id()
            while i < len(lines) and _IS_TASK.match(lines[i]):
                tm = _re.match(r"^[-*]\s+\[([ xX])\]\s*(.*)", lines[i])
                if tm:
                    items.append({"type": "taskItem", "attrs": {"state": "DONE" if tm.group(1).lower() == "x" else "TODO", "localId": _next_id()}, "content": _inline(tm.group(2))})
                i += 1
            nodes.append({"type": "taskList", "attrs": {"localId": list_id}, "content": items})
            continue

        # Unordered list
        if _IS_BULLET.match(line):
            items = []
            while i < len(lines) and _IS_BULLET.match(lines[i]) and not _IS_TASK.match(lines[i]):
                bm = _re.match(r"^[-*]\s+(.*)", lines[i])
                if bm:
                    items.append({"type": "listItem", "content": [{"type": "paragraph", "content": _inline(bm.group(1))}]})
                i += 1
            if items:
                nodes.append({"type": "bulletList", "content": items})
            continue

        # Ordered list
        if _IS_ORDERED.match(line):
            items = []
            while i < len(lines) and _IS_ORDERED.match(lines[i]):
                om = _re.match(r"^\d+[.)]\s+(.*)", lines[i])
                if om:
                    items.append({"type": "listItem", "content": [{"type": "paragraph", "content": _inline(om.group(1))}]})
                i += 1
            if items:
                nodes.append({"type": "orderedList", "content": items})
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Paragraph — collect until blank line or block element
        para: list[str] = []
        while i < len(lines) and lines[i].strip() and not _IS_BLOCK.match(lines[i]):
            para.append(lines[i])
            i += 1
        if para:
            nodes.append({"type": "paragraph", "content": _inline(" ".join(para))})

    if not nodes:
        nodes = [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    return {"type": "doc", "version": 1, "content": nodes}


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

    if node_type == "taskList":
        items = ""
        for child in content:
            items += _adf_node_to_md(child, list_depth)
        return items + "\n"

    if node_type == "taskItem":
        indent = "  " * list_depth
        state = node.get("attrs", {}).get("state", "TODO")
        checkbox = "[x]" if state == "DONE" else "[ ]"
        text = _adf_inline(content)
        return f"{indent}- {checkbox} {text}\n"

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
