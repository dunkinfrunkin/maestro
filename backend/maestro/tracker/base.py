"""Abstract tracker interface — pluggable adapter pattern."""

from __future__ import annotations

from abc import ABC, abstractmethod

from maestro.models import Issue


class TrackerClient(ABC):
    """Base class for issue-tracker adapters.

    Implementations must provide the three operations required by the spec:
    1. fetch_candidate_issues — active issues eligible for dispatch
    2. fetch_issues_by_states — used for startup terminal cleanup
    3. fetch_issue_states_by_ids — used for reconciliation refresh
    """

    @abstractmethod
    async def fetch_candidate_issues(self) -> list[Issue]:
        """Fetch active-state issues from the configured project."""
        ...

    @abstractmethod
    async def fetch_issues_by_states(self, states: list[str]) -> list[Issue]:
        """Fetch issues in the given states (e.g., terminal states for cleanup)."""
        ...

    @abstractmethod
    async def fetch_issue_states_by_ids(self, issue_ids: list[str]) -> dict[str, str]:
        """Return a mapping of issue_id → current state name for reconciliation."""
        ...
