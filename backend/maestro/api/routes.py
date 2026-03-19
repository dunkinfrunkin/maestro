"""FastAPI routes — Symphony HTTP server extension."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from maestro.models import OrchestratorState

router = APIRouter(prefix="/api/v1")


def _get_orchestrator(request: Request):
    orch = request.app.state.orchestrator
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orch


@router.get("/state")
async def get_state(request: Request) -> OrchestratorState:
    """Current system state: running agents, retry queue, aggregate totals."""
    orch = _get_orchestrator(request)
    return orch.state.to_api_state()


@router.get("/config")
async def get_config(request: Request) -> dict:
    """Current service configuration (secrets redacted)."""
    orch = _get_orchestrator(request)
    cfg = orch.config
    return {
        "tracker": {
            "kind": cfg.tracker.kind,
            "endpoint": cfg.tracker.endpoint,
            "project_slug": cfg.tracker.project_slug,
            "api_key_set": bool(cfg.tracker.api_key),
            "active_states": cfg.tracker.active_states,
            "terminal_states": cfg.tracker.terminal_states,
        },
        "polling": {
            "interval_ms": cfg.polling.interval_ms,
        },
        "workspace": {
            "root": cfg.workspace.root,
        },
        "agent": {
            "max_concurrent_agents": cfg.agent.max_concurrent_agents,
            "max_retry_backoff_ms": cfg.agent.max_retry_backoff_ms,
        },
        "codex": {
            "command": cfg.codex.command,
            "turn_timeout_ms": cfg.codex.turn_timeout_ms,
            "stall_timeout_ms": cfg.codex.stall_timeout_ms,
        },
    }


@router.post("/refresh")
async def refresh(request: Request) -> dict:
    """Queue an immediate poll/reconciliation cycle."""
    orch = _get_orchestrator(request)
    orch.trigger_refresh()
    return {"status": "queued"}


@router.get("/issues/{issue_identifier}")
async def get_issue(issue_identifier: str, request: Request) -> dict:
    """Issue-specific details."""
    orch = _get_orchestrator(request)
    api_state = orch.state.to_api_state()

    running_match = None
    for attempt in api_state.running.values():
        if attempt.issue_identifier == issue_identifier:
            running_match = attempt
            break

    retry_match = None
    for entry in api_state.retrying.values():
        if entry.issue_identifier == issue_identifier:
            retry_match = entry
            break

    if not running_match and not retry_match:
        raise HTTPException(status_code=404, detail="Issue not found")

    return {
        "issue_identifier": issue_identifier,
        "running": running_match,
        "retrying": retry_match,
    }
