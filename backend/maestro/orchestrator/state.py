"""Orchestrator runtime state — the single mutable authority."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from maestro.models import CodexTotals, OrchestratorState, RetryEntry, RunAttempt


@dataclass
class RuntimeState:
    """In-memory orchestrator state. No persistent DB required (per spec)."""

    running: dict[str, RunAttempt] = field(default_factory=dict)
    claimed: set[str] = field(default_factory=set)
    retry_queue: dict[str, RetryEntry] = field(default_factory=dict)
    codex_totals: CodexTotals = field(default_factory=CodexTotals)
    rate_limits: dict[str, Any] = field(default_factory=dict)

    def claim(self, issue_id: str) -> bool:
        """Claim an issue to prevent duplicate dispatch. Returns False if already claimed."""
        if issue_id in self.claimed or issue_id in self.running:
            return False
        self.claimed.add(issue_id)
        return True

    def release(self, issue_id: str) -> None:
        """Release a claim."""
        self.claimed.discard(issue_id)
        self.running.pop(issue_id, None)
        self.retry_queue.pop(issue_id, None)

    def add_running(self, issue_id: str, attempt: RunAttempt) -> None:
        """Mark an issue as running."""
        self.running[issue_id] = attempt
        self.retry_queue.pop(issue_id, None)

    def remove_running(self, issue_id: str) -> RunAttempt | None:
        """Remove from running, return the attempt if it existed."""
        return self.running.pop(issue_id, None)

    def schedule_retry(self, entry: RetryEntry) -> None:
        """Add an issue to the retry queue."""
        self.retry_queue[entry.issue_id] = entry

    def running_count(self) -> int:
        return len(self.running)

    def running_count_by_state(self, state: str) -> int:
        return sum(1 for a in self.running.values() if a.status.value != "succeeded")

    def available_slots(self, max_concurrent: int) -> int:
        return max(0, max_concurrent - self.running_count())

    def to_api_state(self) -> OrchestratorState:
        """Snapshot for the HTTP API."""
        return OrchestratorState(
            running=dict(self.running),
            retrying=dict(self.retry_queue),
            codex_totals=self.codex_totals,
            rate_limits=dict(self.rate_limits),
        )
