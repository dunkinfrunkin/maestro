"""Tests for Linear tracker client (using mocked HTTP responses)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maestro.tracker.linear import LinearClient, _normalize_issue


@pytest.fixture
def sample_issue_node():
    return {
        "id": "issue-1",
        "identifier": "PROJ-123",
        "title": "Fix the login bug",
        "description": "Users can't log in on mobile",
        "priority": 2,
        "url": "https://linear.app/team/issue/PROJ-123",
        "createdAt": "2025-01-15T10:00:00.000Z",
        "updatedAt": "2025-01-16T12:00:00.000Z",
        "branchName": "fix-login-bug",
        "state": {"name": "In Progress"},
        "labels": {"nodes": [{"name": "Bug"}, {"name": "Mobile"}]},
        "relations": {
            "nodes": [
                {
                    "type": "blocks",
                    "relatedIssue": {"id": "issue-0", "identifier": "PROJ-100"},
                },
                {
                    "type": "related",
                    "relatedIssue": {"id": "issue-2", "identifier": "PROJ-200"},
                },
            ]
        },
    }


def test_normalize_issue(sample_issue_node):
    issue = _normalize_issue(sample_issue_node)
    assert issue.id == "issue-1"
    assert issue.identifier == "PROJ-123"
    assert issue.title == "Fix the login bug"
    assert issue.state == "In Progress"
    assert issue.branch_name == "fix-login-bug"
    assert issue.labels == ["bug", "mobile"]  # lowercased
    assert issue.blocked_by == ["issue-0"]  # only "blocks" type
    assert issue.priority == 2
    assert issue.created_at is not None


def test_normalize_issue_null_priority():
    node = {
        "id": "i1",
        "identifier": "X-1",
        "title": "T",
        "state": {"name": "Todo"},
        "labels": {"nodes": []},
        "relations": {"nodes": []},
    }
    issue = _normalize_issue(node)
    assert issue.priority is None


def test_normalize_issue_non_int_priority():
    node = {
        "id": "i1",
        "identifier": "X-1",
        "title": "T",
        "priority": "high",
        "state": {"name": "Todo"},
        "labels": {"nodes": []},
        "relations": {"nodes": []},
    }
    issue = _normalize_issue(node)
    assert issue.priority is None


@pytest.mark.asyncio
async def test_fetch_candidate_issues(sample_issue_node):
    client = LinearClient(
        api_key="test-key",
        project_slug="my-proj",
        active_states=["Todo", "In Progress"],
        terminal_states=["Done"],
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "issues": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [sample_issue_node],
            }
        }
    }

    with patch.object(client._http, "post", AsyncMock(return_value=mock_response)) as mock_post:
        issues = await client.fetch_candidate_issues()

    assert len(issues) == 1
    assert issues[0].identifier == "PROJ-123"
    mock_post.assert_called_once()

    await client.close()


@pytest.mark.asyncio
async def test_fetch_issue_states_by_ids():
    client = LinearClient(
        api_key="test-key",
        project_slug="my-proj",
        active_states=["Todo"],
        terminal_states=["Done"],
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "nodes": [
                {"id": "id-1", "state": {"name": "Done"}},
                {"id": "id-2", "state": {"name": "In Progress"}},
            ]
        }
    }

    with patch.object(client._http, "post", AsyncMock(return_value=mock_response)):
        states = await client.fetch_issue_states_by_ids(["id-1", "id-2"])

    assert states == {"id-1": "Done", "id-2": "In Progress"}
    await client.close()


@pytest.mark.asyncio
async def test_fetch_issue_states_empty():
    client = LinearClient(
        api_key="k",
        project_slug="p",
        active_states=[],
        terminal_states=[],
    )
    result = await client.fetch_issue_states_by_ids([])
    assert result == {}
    await client.close()
