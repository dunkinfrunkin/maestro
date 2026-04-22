"""Backwards-compatible re-export — use maestro.external.linear instead."""

from maestro.external.linear.tracker import LinearIssueTracker as LinearClient  # noqa: F401
from maestro.external.linear.tracker import LinearGraphQLError  # noqa: F401
from maestro.external.linear.tracker import _normalize_issue  # noqa: F401

__all__ = ["LinearClient", "LinearGraphQLError", "_normalize_issue"]
