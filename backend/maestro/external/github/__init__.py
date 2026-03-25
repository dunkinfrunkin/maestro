"""GitHub integration — issue tracker and code host."""

from maestro.external.github.tracker import GitHubIssueTracker
from maestro.external.github.codehost import GitHubCodeHost

# Backwards-compatible alias
GitHubClient = GitHubIssueTracker

__all__ = ["GitHubIssueTracker", "GitHubCodeHost", "GitHubClient"]
