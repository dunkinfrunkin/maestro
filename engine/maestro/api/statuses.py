"""API routes for pipeline statuses."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

STATUSES = [
    {"value": "todo", "label": "To Do", "color": "gray", "active": True, "order": 1},
    {"value": "in_progress", "label": "In Progress", "color": "blue", "active": True, "order": 2},
    {"value": "pending_approval", "label": "Pending Approval", "color": "purple", "active": True, "order": 3},
    {"value": "approved", "label": "Approved", "color": "teal", "active": False, "order": 4},
    {"value": "promote", "label": "Promote", "color": "yellow", "active": False, "order": 5},
    {"value": "deploy", "label": "Deploy", "color": "orange", "active": False, "order": 6},
    {"value": "done", "label": "Done", "color": "green", "active": True, "order": 7},
    {"value": "failed", "label": "Failed", "color": "red", "active": True, "order": 8},
    {"value": "halted", "label": "Halted", "color": "gray", "active": True, "order": 9},
]

LEGACY_MAP = {
    "queued": "todo",
    "implement": "in_progress",
    "review": "in_progress",
    "risk_profile": "in_progress",
    "monitor": "deploy",
}


@router.get("/statuses")
async def list_statuses() -> list[dict]:
    """Return all pipeline statuses with display metadata."""
    return STATUSES


@router.get("/statuses/legacy-map")
async def get_legacy_map() -> dict:
    """Return mapping from legacy status values to new ones."""
    return LEGACY_MAP
