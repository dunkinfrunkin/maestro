"""FastAPI routes — Symphony HTTP server extension."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from maestro.models import OrchestratorState

router = APIRouter(prefix="/api/v1")

# Will be replaced with a real reference once the orchestrator is wired up.
_state = OrchestratorState()


def set_orchestrator_state(state: OrchestratorState) -> None:
    global _state
    _state = state


@router.get("/state")
async def get_state() -> OrchestratorState:
    """Current system state: running agents, retry queue, aggregate totals."""
    return _state


@router.get("/{issue_identifier}")
async def get_issue(issue_identifier: str) -> dict:
    """Issue-specific details."""
    attempt = _state.running.get(issue_identifier)
    retry = _state.retrying.get(issue_identifier)
    if not attempt and not retry:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {
        "issue_identifier": issue_identifier,
        "running": attempt,
        "retrying": retry,
    }


@router.post("/refresh")
async def refresh() -> dict:
    """Queue an immediate poll/reconciliation cycle."""
    # Will trigger the orchestrator's poll loop once wired up.
    return {"status": "queued"}
