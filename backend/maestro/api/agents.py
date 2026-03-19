"""API routes for agent configuration and API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from maestro.auth import get_current_user
from maestro.db import crud
from maestro.db.engine import get_session
from maestro.db.models import AgentType, ApiKeyProvider, User
from maestro.agent.implementation import AVAILABLE_MODELS, DEFAULT_MODEL

router = APIRouter(prefix="/api/v1")


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


class AgentConfigUpdate(BaseModel):
    model: str


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

    return AgentConfigResponse(
        agent_type=agent_type,
        model=config.model if config else DEFAULT_MODEL,
        active=api_key is not None,
        available_models=AVAILABLE_MODELS,
    )


@router.put("/workspaces/{workspace_id}/agents/{agent_type}")
async def update_agent_config(
    workspace_id: int,
    agent_type: str,
    body: AgentConfigUpdate,
    user: User = Depends(get_current_user),
) -> AgentConfigResponse:
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")

    valid_models = [m["id"] for m in AVAILABLE_MODELS]
    if body.model not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Valid: {valid_models}")

    async with get_session() as session:
        config = await crud.set_agent_config(session, workspace_id, at, body.model)
        api_key = await crud.get_api_key(session, workspace_id, ApiKeyProvider.ANTHROPIC)

    return AgentConfigResponse(
        agent_type=agent_type,
        model=config.model,
        active=api_key is not None,
        available_models=AVAILABLE_MODELS,
    )
