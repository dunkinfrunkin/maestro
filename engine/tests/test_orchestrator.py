"""Tests for orchestrator state and eligibility logic."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from maestro.models import Issue, RetryEntry, RunAttempt, RunAttemptStatus
from maestro.orchestrator.engine import _issue_sort_key
from maestro.orchestrator.state import RuntimeState


# ---------------------------------------------------------------------------
# RuntimeState
# ---------------------------------------------------------------------------


def test_claim_and_release():
    state = RuntimeState()
    assert state.claim("id-1") is True
    assert state.claim("id-1") is False  # already claimed
    state.release("id-1")
    assert state.claim("id-1") is True  # can re-claim after release


def test_add_running_prevents_claim():
    state = RuntimeState()
    attempt = RunAttempt(issue_id="id-1", issue_identifier="X-1", workspace_path="/tmp/x")
    state.add_running("id-1", attempt)
    assert state.claim("id-1") is False


def test_running_count_and_slots():
    state = RuntimeState()
    assert state.running_count() == 0
    assert state.available_slots(4) == 4

    attempt = RunAttempt(issue_id="id-1", issue_identifier="X-1", workspace_path="/tmp/x")
    state.add_running("id-1", attempt)
    assert state.running_count() == 1
    assert state.available_slots(4) == 3


def test_schedule_retry():
    state = RuntimeState()
    entry = RetryEntry(
        issue_id="id-1",
        issue_identifier="X-1",
        attempt_number=2,
        scheduled_at=datetime.now(timezone.utc),
        backoff_ms=10000,
    )
    state.schedule_retry(entry)
    assert "id-1" in state.retry_queue

    # Adding to running should clear retry
    attempt = RunAttempt(issue_id="id-1", issue_identifier="X-1", workspace_path="/tmp/x")
    state.add_running("id-1", attempt)
    assert "id-1" not in state.retry_queue


def test_to_api_state():
    state = RuntimeState()
    attempt = RunAttempt(issue_id="id-1", issue_identifier="X-1", workspace_path="/tmp/x")
    state.add_running("id-1", attempt)
    api = state.to_api_state()
    assert "id-1" in api.running
    assert api.codex_totals.total_input_tokens == 0


# ---------------------------------------------------------------------------
# Issue sorting
# ---------------------------------------------------------------------------


def test_issue_sort_key_priority():
    i1 = Issue(id="1", identifier="A-1", title="", state="Todo", priority=1)
    i2 = Issue(id="2", identifier="A-2", title="", state="Todo", priority=3)
    i3 = Issue(id="3", identifier="A-3", title="", state="Todo", priority=None)

    sorted_issues = sorted([i3, i2, i1], key=_issue_sort_key)
    assert [i.identifier for i in sorted_issues] == ["A-1", "A-2", "A-3"]


def test_issue_sort_key_created_at():
    i1 = Issue(
        id="1",
        identifier="A-1",
        title="",
        state="Todo",
        priority=1,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    i2 = Issue(
        id="2",
        identifier="A-2",
        title="",
        state="Todo",
        priority=1,
        created_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    sorted_issues = sorted([i2, i1], key=_issue_sort_key)
    assert sorted_issues[0].identifier == "A-1"
