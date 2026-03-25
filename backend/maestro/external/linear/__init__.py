"""Linear integration — issue tracker only."""

from maestro.external.linear.tracker import LinearIssueTracker

# Backwards-compatible alias
LinearClient = LinearIssueTracker

__all__ = ["LinearIssueTracker", "LinearClient"]
