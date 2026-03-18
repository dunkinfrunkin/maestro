"""Core domain models based on the Symphony specification."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Issue (normalized tracker record)
# ---------------------------------------------------------------------------


class Issue(BaseModel):
    id: str
    identifier: str
    title: str
    description: str | None = None
    priority: int | None = None
    state: str
    branch_name: str | None = None
    url: str | None = None
    labels: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Orchestrator state machine
# ---------------------------------------------------------------------------


class IssueStatus(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    RUNNING = "running"
    RETRY_QUEUED = "retry_queued"
    RELEASED = "released"


class RunAttemptStatus(str, Enum):
    PREPARING_WORKSPACE = "preparing_workspace"
    BUILDING_PROMPT = "building_prompt"
    LAUNCHING_AGENT = "launching_agent"
    INITIALIZING_SESSION = "initializing_session"
    STREAMING_TURN = "streaming_turn"
    FINISHING = "finishing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    STALLED = "stalled"
    CANCELED = "canceled"


class RunAttempt(BaseModel):
    issue_id: str
    issue_identifier: str
    workspace_path: str
    attempt_number: int = 1
    status: RunAttemptStatus = RunAttemptStatus.PREPARING_WORKSPACE
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class LiveSession(BaseModel):
    session_id: str
    thread_id: str
    turn_id: str
    turn_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: datetime | None = None
    last_event_at: datetime | None = None


class RetryEntry(BaseModel):
    issue_id: str
    issue_identifier: str
    attempt_number: int
    scheduled_at: datetime
    backoff_ms: int


class CodexTotals(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_seconds_running: float = 0.0


class OrchestratorState(BaseModel):
    running: dict[str, RunAttempt] = Field(default_factory=dict)
    retrying: dict[str, RetryEntry] = Field(default_factory=dict)
    codex_totals: CodexTotals = Field(default_factory=CodexTotals)
    rate_limits: dict[str, Any] = Field(default_factory=dict)
