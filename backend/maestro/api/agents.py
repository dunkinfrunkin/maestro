"""API routes for agent configuration and API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from maestro.auth import get_current_user
from maestro.db import crud
from maestro.db.engine import get_session
from sqlalchemy import select

from maestro.db.models import AgentRun, AgentType, ApiKeyProvider, User
from maestro.agent.implementation import AVAILABLE_MODELS, DEFAULT_MODEL
from maestro.agent.plugin import registry

router = APIRouter(prefix="/api/v1")


@router.get("/plugins")
async def list_plugins(user: User = Depends(get_current_user)) -> list[dict]:
    """List all registered agent plugins (built-in + custom)."""
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "description": p.description,
            "trigger_status": p.trigger_status,
            "configurable_fields": p.configurable_fields,
        }
        for p in registry.list_all()
    ]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ApiKeySet(BaseModel):
    key: str


class ApiKeyStatus(BaseModel):
    provider: str
    has_key: bool
    updated_at: str | None = None


class AgentConfigResponse(BaseModel):
    agent_type: str
    model: str
    active: bool  # has API key
    available_models: list[dict]
    extra_config: dict = {}


class AgentConfigUpdate(BaseModel):
    model: str | None = None
    extra_config: dict | None = None


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/api-keys/{provider}")
async def get_api_key_status(
    workspace_id: int,
    provider: str,
    user: User = Depends(get_current_user),
) -> ApiKeyStatus:
    try:
        p = ApiKeyProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    async with get_session() as session:
        api_key = await crud.get_api_key(session, workspace_id, p)

    return ApiKeyStatus(
        provider=provider,
        has_key=api_key is not None,
        updated_at=api_key.updated_at.isoformat() if api_key and api_key.updated_at else None,
    )


@router.put("/workspaces/{workspace_id}/api-keys/{provider}")
async def set_api_key(
    workspace_id: int,
    provider: str,
    body: ApiKeySet,
    user: User = Depends(get_current_user),
) -> ApiKeyStatus:
    try:
        p = ApiKeyProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    async with get_session() as session:
        api_key = await crud.set_api_key(session, workspace_id, p, body.key)

    return ApiKeyStatus(
        provider=provider,
        has_key=True,
        updated_at=api_key.updated_at.isoformat() if api_key.updated_at else None,
    )


@router.delete("/workspaces/{workspace_id}/api-keys/{provider}")
async def delete_api_key(
    workspace_id: int,
    provider: str,
    user: User = Depends(get_current_user),
) -> dict:
    try:
        p = ApiKeyProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    async with get_session() as session:
        ok = await crud.delete_api_key(session, workspace_id, p)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Agent Config
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/agents/{agent_type}")
async def get_agent_config(
    workspace_id: int,
    agent_type: str,
    user: User = Depends(get_current_user),
) -> AgentConfigResponse:
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")

    async with get_session() as session:
        config = await crud.get_agent_config(session, workspace_id, at)
        api_key = await crud.get_api_key(session, workspace_id, ApiKeyProvider.ANTHROPIC)

    import json
    extra = {}
    if config and config.extra_config:
        try:
            extra = json.loads(config.extra_config)
        except (json.JSONDecodeError, TypeError):
            pass

    return AgentConfigResponse(
        agent_type=agent_type,
        model=config.model if config else DEFAULT_MODEL,
        active=api_key is not None,
        available_models=AVAILABLE_MODELS,
        extra_config=extra,
    )


@router.put("/workspaces/{workspace_id}/agents/{agent_type}")
async def update_agent_config(
    workspace_id: int,
    agent_type: str,
    body: AgentConfigUpdate,
    user: User = Depends(get_current_user),
) -> AgentConfigResponse:
    import json

    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")

    model = body.model or DEFAULT_MODEL
    valid_models = [m["id"] for m in AVAILABLE_MODELS]
    if model not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Valid: {valid_models}")

    extra_json = json.dumps(body.extra_config) if body.extra_config is not None else None

    async with get_session() as session:
        config = await crud.set_agent_config(session, workspace_id, at, model, extra_json)
        api_key = await crud.get_api_key(session, workspace_id, ApiKeyProvider.ANTHROPIC)

    extra = {}
    if config.extra_config:
        try:
            extra = json.loads(config.extra_config)
        except (json.JSONDecodeError, TypeError):
            pass

    return AgentConfigResponse(
        agent_type=agent_type,
        model=config.model,
        active=api_key is not None,
        available_models=AVAILABLE_MODELS,
        extra_config=extra,
    )


# ---------------------------------------------------------------------------
# Agent Runs
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/agent-runs")
async def list_agent_runs(
    workspace_id: int,
    user: User = Depends(get_current_user),
    limit: int = 20,
) -> list[dict]:
    """List recent agent runs for a workspace."""
    async with get_session() as session:
        result = await session.execute(
            select(AgentRun)
            .where(AgentRun.workspace_id == workspace_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        runs = result.scalars().all()

    return [
        {
            "id": r.id,
            "agent_type": r.agent_type.value if r.agent_type else "",
            "task_pipeline_id": r.task_pipeline_id,
            "status": r.status.value if r.status else "",
            "model": r.model,
            "summary": r.summary,
            "error": r.error,
            "cost_usd": r.cost_usd,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]
