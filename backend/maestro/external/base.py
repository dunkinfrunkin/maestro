"""Abstract interfaces for external integrations.

Two interfaces:
- IssueTracker: fetch/sync issues (GitHub Issues, Linear, Jira)
- CodeHost: PR operations (GitHub, GitLab, Bitbucket)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from maestro.models import Issue


# ---------------------------------------------------------------------------
# Issue tracker interface
# ---------------------------------------------------------------------------


class IssueTracker(ABC):
    """Fetch and sync issues from an external tracker.

    Implementations: GitHub Issues, Linear, Jira (future).
    """

    @abstractmethod
    async def fetch_candidate_issues(self, max_results: int = 100, user_email: str = "") -> list[Issue]:
        """Fetch active issues eligible for pipeline dispatch.

        If user_email is provided, filter to issues assigned to that user.
        """
        ...

    @abstractmethod
    async def fetch_issues_by_states(self, states: list[str], user_email: str = "") -> list[Issue]:
        """Fetch issues in the given states (e.g., terminal states for cleanup)."""
        ...

    @abstractmethod
    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        """Return a mapping of issue_id -> current state name."""
        ...

    async def search_issues(self, query: str) -> list[Issue]:
        """Search issues. Optional — not all trackers support search."""
        raise NotImplementedError

    async def close(self) -> None:
        """Clean up resources (HTTP clients, etc.)."""
        pass


# ---------------------------------------------------------------------------
# Code host interface
# ---------------------------------------------------------------------------


@dataclass
class ReviewResult:
    status: str  # "posted", "failed"
    review_id: str | None = None
    html_url: str = ""
    error: str = ""


@dataclass
class MergeResult:
    status: str  # "merged", "failed"
    sha: str = ""
    error: str = ""


@dataclass
class CICheck:
    name: str
    status: str  # "passed", "failed", "pending", "running"
    url: str = ""


@dataclass
class CIStatus:
    checks: list[CICheck] = field(default_factory=list)
    all_passed: bool = False


@dataclass
class PRComment:
    id: str
    body: str
    path: str = ""
    line: int = 0
    user: str = ""
    reply_count: int = 0


class CodeHost(ABC):
    """PR/MR operations on a code hosting platform.

    Implementations: GitHub, GitLab (future), Bitbucket (future).
    """

    @abstractmethod
    async def create_review(
        self,
        repo: str,
        pr_number: int,
        comments: list[dict[str, Any]],
        verdict: str = "COMMENT",
        summary: str = "",
    ) -> ReviewResult:
        """Post a review with inline comments on a PR/MR."""
        ...

    @abstractmethod
    async def reply_to_comment(
        self, repo: str, comment_id: str, body: str
    ) -> None:
        """Reply to an existing review comment in a thread."""
        ...

    @abstractmethod
    async def resolve_thread(self, repo: str, thread_id: str) -> None:
        """Resolve/close a review thread."""
        ...

    @abstractmethod
    async def merge_pr(
        self, repo: str, pr_number: int, strategy: str = "squash"
    ) -> MergeResult:
        """Merge a PR/MR with the given strategy."""
        ...

    @abstractmethod
    async def get_ci_status(self, repo: str, pr_number: int) -> CIStatus:
        """Get CI/CD check status for a PR/MR."""
        ...

    @abstractmethod
    async def get_pr_comments(
        self, repo: str, pr_number: int
    ) -> list[PRComment]:
        """Get all review comments on a PR/MR."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        pass
