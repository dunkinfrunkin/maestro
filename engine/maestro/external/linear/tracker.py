"""Linear GraphQL tracker — implements IssueTracker interface."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from maestro.external.base import IssueTracker
from maestro.models import Issue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL fragments & queries
# ---------------------------------------------------------------------------

_ISSUE_FRAGMENT = """
fragment IssueFields on Issue {
  id
  identifier
  title
  description
  priority
  url
  createdAt
  updatedAt
  branchName
  state { name }
  labels { nodes { name } }
  relations(first: 50) {
    nodes {
      type
      relatedIssue { id identifier }
    }
  }
}
"""

_FETCH_CANDIDATES = (
    _ISSUE_FRAGMENT
    + """
query FetchCandidates($projectSlug: String!, $states: [String!]!, $after: String) {
  issues(
    filter: {
      project: { slugId: { eq: $projectSlug } }
      state: { name: { in: $states } }
    }
    first: 50
    after: $after
  ) {
    pageInfo { hasNextPage endCursor }
    nodes { ...IssueFields }
  }
}
"""
)

_FETCH_BY_STATES = (
    _ISSUE_FRAGMENT
    + """
query FetchByStates($projectSlug: String!, $states: [String!]!, $after: String) {
  issues(
    filter: {
      project: { slugId: { eq: $projectSlug } }
      state: { name: { in: $states } }
    }
    first: 50
    after: $after
  ) {
    pageInfo { hasNextPage endCursor }
    nodes { ...IssueFields }
  }
}
"""
)

_FETCH_STATES_BY_IDS = """
query FetchStatesByIds($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Issue {
      id
      state { name }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LinearIssueTracker(IssueTracker):
    """Linear GraphQL issue-tracker adapter."""

    def __init__(
        self,
        api_key: str,
        project_slug: str,
        active_states: list[str],
        terminal_states: list[str],
        endpoint: str = "https://api.linear.app/graphql",
        timeout_ms: int = 30000,
    ) -> None:
        self._api_key = api_key
        self._project_slug = project_slug
        self._active_states = active_states
        self._terminal_states = terminal_states
        self._endpoint = endpoint
        self._timeout = timeout_ms / 1000.0
        self._http = httpx.AsyncClient(
            base_url=endpoint,
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            timeout=self._timeout,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def fetch_candidate_issues(self, max_results: int = 100, user_email: str = "") -> list[Issue]:
        return await self._paginated_issues(
            _FETCH_CANDIDATES,
            {"projectSlug": self._project_slug, "states": self._active_states},
            max_results=max_results,
        )

    async def fetch_issues_by_states(self, states: list[str], user_email: str = "") -> list[Issue]:
        return await self._paginated_issues(
            _FETCH_BY_STATES,
            {"projectSlug": self._project_slug, "states": states},
        )

    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        if not issue_ids:
            return {}
        data = await self._execute(_FETCH_STATES_BY_IDS, {"ids": issue_ids})
        result: dict[str, str] = {}
        for node in data.get("nodes", []):
            if node and "id" in node and "state" in node:
                result[node["id"]] = node["state"]["name"]
        return result

    async def execute_graphql(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        """Execute a raw GraphQL query (for the optional linear_graphql tool)."""
        return await self._execute(query, variables or {})

    async def _execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        resp = await self._http.post("", json={"query": query, "variables": variables})
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise LinearGraphQLError(body["errors"])
        return body.get("data", {})

    async def _paginated_issues(
        self, query: str, variables: dict[str, Any], max_results: int = 100
    ) -> list[Issue]:
        all_issues: list[Issue] = []
        cursor: str | None = None
        while True:
            v = {**variables, "after": cursor}
            data = await self._execute(query, v)
            issues_data = data.get("issues", {})
            for node in issues_data.get("nodes", []):
                all_issues.append(_normalize_issue(node))
            if len(all_issues) >= max_results:
                break
            page_info = issues_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break
        return all_issues[:max_results]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _normalize_issue(node: dict[str, Any]) -> Issue:
    labels = [
        label["name"].lower()
        for label in (node.get("labels", {}).get("nodes") or [])
    ]

    blocked_by: list[str] = []
    for rel in (node.get("relations", {}).get("nodes") or []):
        if rel.get("type") == "blocks" and rel.get("relatedIssue"):
            blocked_by.append(rel["relatedIssue"]["id"])

    priority = node.get("priority")
    if not isinstance(priority, int):
        priority = None

    return Issue(
        id=node["id"],
        identifier=node["identifier"],
        title=node["title"],
        description=node.get("description"),
        priority=priority,
        state=node["state"]["name"],
        branch_name=node.get("branchName"),
        url=node.get("url"),
        labels=labels,
        blocked_by=blocked_by,
        created_at=_parse_dt(node.get("createdAt")),
        updated_at=_parse_dt(node.get("updatedAt")),
    )


def _parse_dt(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class LinearGraphQLError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(f"Linear GraphQL errors: {errors}")
