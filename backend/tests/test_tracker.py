"""Tests for tracker clients (GitHub and Linear) using mocked HTTP responses."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maestro.tracker.github import GitHubClient, _normalize_issue as github_normalize_issue
from maestro.tracker.linear import LinearClient, _normalize_issue


# ---------------------------------------------------------------------------
# GitHub tracker tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_github_issue():
    return {
        "number": 42,
        "title": "Add dark mode support",
        "body": "Users have requested a dark mode option.",
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/42",
        "created_at": "2025-03-01T09:00:00Z",
        "updated_at": "2025-03-10T14:30:00Z",
        "labels": [
            {"name": "enhancement"},
            {"name": "Priority:2"},
        ],
        "repository": {"full_name": "owner/repo"},
    }


def test_github_normalize_issue(sample_github_issue):
    issue = github_normalize_issue(sample_github_issue, "owner/repo")
    assert issue.id == "42"
    assert issue.identifier == "owner/repo#42"
    assert issue.title == "Add dark mode support"
    assert issue.description == "Users have requested a dark mode option."
    assert issue.state == "open"
    assert issue.url == "https://github.com/owner/repo/issues/42"
    assert "enhancement" in issue.labels
    assert "priority:2" in issue.labels
    assert issue.priority == 2
    assert issue.created_at is not None
    assert issue.updated_at is not None
    assert issue.blocked_by == []
    assert issue.branch_name is None


def test_github_normalize_issue_no_repo():
    item = {
        "number": 7,
        "title": "Bug report",
        "body": None,
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/7",
        "created_at": None,
        "updated_at": None,
        "labels": [],
    }
    issue = github_normalize_issue(item, "")
    assert issue.id == "7"
    assert issue.identifier == "#7"
    assert issue.priority is None
    assert issue.labels == []


def test_github_normalize_issue_invalid_priority_label():
    item = {
        "number": 5,
        "title": "Edge case",
        "body": None,
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/5",
        "created_at": None,
        "updated_at": None,
        "labels": [{"name": "priority:high"}],
    }
    issue = github_normalize_issue(item, "owner/repo")
    # "high" is not an int, so priority should remain None
    assert issue.priority is None


@pytest.mark.asyncio
async def test_github_fetch_candidate_issues_specific_repo(sample_github_issue):
    client = GitHubClient(token="test-token", repo="owner/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # First page returns one issue; second page returns empty to stop pagination.
    mock_response.json.side_effect = [[sample_github_issue], []]

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)):
        issues = await client.fetch_candidate_issues()

    assert len(issues) == 1
    assert issues[0].identifier == "owner/repo#42"
    assert issues[0].title == "Add dark mode support"

    await client.close()


@pytest.mark.asyncio
async def test_github_fetch_candidate_issues_skips_pull_requests(sample_github_issue):
    """Issues that have a 'pull_request' key should be excluded."""
    pr_item = {**sample_github_issue, "pull_request": {"url": "https://..."}}
    client = GitHubClient(token="test-token", repo="owner/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.side_effect = [[pr_item], []]

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)):
        issues = await client.fetch_candidate_issues()

    assert issues == []
    await client.close()


@pytest.mark.asyncio
async def test_github_fetch_candidate_issues_all_repos(sample_github_issue):
    """When no repo is set, _fetch_all_issues via /user/issues is used."""
    client = GitHubClient(token="test-token")  # no repo

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.side_effect = [[sample_github_issue], []]

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)) as mock_get:
        issues = await client.fetch_candidate_issues()

    # Should call /user/issues endpoint
    first_call_url = mock_get.call_args_list[0][0][0]
    assert first_call_url == "/user/issues"
    assert len(issues) == 1

    await client.close()


@pytest.mark.asyncio
async def test_github_search_issues(sample_github_issue):
    client = GitHubClient(token="test-token", repo="owner/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                **sample_github_issue,
                "repository_url": "https://api.github.com/repos/owner/repo",
            }
        ]
    }

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)) as mock_get:
        issues = await client.search_issues("dark mode")

    assert len(issues) == 1
    assert issues[0].title == "Add dark mode support"

    # Verify the search query includes the repo filter
    call_kwargs = mock_get.call_args
    params = call_kwargs[1].get("params", {})
    assert "dark mode is:issue" in params["q"]
    assert "repo:owner/repo" in params["q"]

    await client.close()


@pytest.mark.asyncio
async def test_github_search_issues_no_repo():
    """Search without a repo filter should not append repo: qualifier."""
    client = GitHubClient(token="test-token")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"items": []}

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)) as mock_get:
        issues = await client.search_issues("memory leak")

    assert issues == []
    call_kwargs = mock_get.call_args
    params = call_kwargs[1].get("params", {})
    assert "repo:" not in params["q"]

    await client.close()


@pytest.mark.asyncio
async def test_github_fetch_repos():
    client = GitHubClient(token="test-token")

    repo_item = {
        "full_name": "owner/my-repo",
        "name": "my-repo",
        "owner": {"login": "owner"},
        "private": False,
        "open_issues_count": 5,
        "html_url": "https://github.com/owner/my-repo",
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # First page has one repo; second page empty to stop pagination.
    mock_response.json.side_effect = [[repo_item], []]

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)):
        repos = await client.fetch_repos()

    assert len(repos) == 1
    assert repos[0]["full_name"] == "owner/my-repo"
    assert repos[0]["open_issues_count"] == 5
    assert repos[0]["private"] is False

    await client.close()


@pytest.mark.asyncio
async def test_github_fetch_issue_states_by_ids():
    client = GitHubClient(token="test-token")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"state": "closed"}

    with patch.object(client._http, "get", AsyncMock(return_value=mock_response)):
        states = await client.fetch_issue_states_by_ids(["owner/repo#42"])

    assert states == {"owner/repo#42": "closed"}
    await client.close()


@pytest.mark.asyncio
async def test_github_fetch_issue_states_empty():
    client = GitHubClient(token="test-token")
    states = await client.fetch_issue_states_by_ids([])
    assert states == {}
    await client.close()


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
