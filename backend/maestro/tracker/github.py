"""Backwards-compatible re-export — use maestro.external.github instead."""

from maestro.external.github.tracker import GitHubIssueTracker as GitHubClient  # noqa: F401

__all__ = ["GitHubClient"]
