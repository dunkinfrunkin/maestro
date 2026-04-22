"""API routes for agent configuration and API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from maestro.auth import get_current_user
from maestro.db import crud
from maestro.db.engine import get_session
from sqlalchemy import select

from maestro.db.models import AgentRun, AgentType, ApiKeyProvider, User
from maestro.agents.implementation import DEFAULT_MODEL
from maestro.agents.plugin import registry

PROVIDER_MODELS: dict[str, list[dict]] = {
    "anthropic": [
        {"id": "sonnet", "name": "Claude Sonnet", "description": "Best speed/intelligence balance"},
        {"id": "opus", "name": "Claude Opus", "description": "Most capable, best for complex tasks"},
        {"id": "haiku", "name": "Claude Haiku", "description": "Fastest, good for simple tasks"},
    ],
    "openai": [
        {"id": "gpt-5.3-codex", "name": "GPT-5.3 Codex", "description": "Agentic coding model, state-of-the-art on SWE-Bench"},
        {"id": "gpt-5.4", "name": "GPT-5.4", "description": "Latest frontier model, unified text and image"},
        {"id": "o4-mini", "name": "o4-mini", "description": "Fast reasoning, Codex CLI default"},
    ],
}

PROVIDER_DEFAULTS: dict[str, str] = {
    "anthropic": "sonnet",
    "openai": "gpt-5.3-codex",
}

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


@router.get("/agents/{agent_type}/default-prompt")
async def get_default_prompt(agent_type: str, user: User = Depends(get_current_user)) -> dict:
    """Get the default system prompt for an agent type."""
    try:
        mod = __import__(f"maestro.agents.{agent_type}", fromlist=["SYSTEM_PROMPT"])
        prompt = getattr(mod, "SYSTEM_PROMPT", "")
    except (ImportError, AttributeError):
        prompt = ""
    return {"agent_type": agent_type, "default_prompt": prompt}


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
    provider: str
    model: str
    active: bool  # has API key for the selected provider
    available_models: list[dict]
    providers: list[dict]
    extra_config: dict = {}


class AgentConfigUpdate(BaseModel):
    provider: str | None = None
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
        provider = config.provider if config else "anthropic"
        try:
            provider_enum = ApiKeyProvider(provider)
        except ValueError:
            provider_enum = ApiKeyProvider.ANTHROPIC
        api_key = await crud.get_api_key(session, workspace_id, provider_enum)

    import json
    extra = {}
    if config and config.extra_config:
        try:
            extra = json.loads(config.extra_config)
        except (json.JSONDecodeError, TypeError):
            pass

    return AgentConfigResponse(
        agent_type=agent_type,
        provider=provider,
        model=config.model if config else PROVIDER_DEFAULTS.get(provider, DEFAULT_MODEL),
        active=api_key is not None,
        available_models=PROVIDER_MODELS.get(provider, PROVIDER_MODELS["anthropic"]),
        providers=[{"id": k, "name": k.title(), "models": v} for k, v in PROVIDER_MODELS.items()],
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

    provider = body.provider or "anthropic"
    if provider not in PROVIDER_MODELS:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Valid: {list(PROVIDER_MODELS.keys())}")

    model = body.model or PROVIDER_DEFAULTS.get(provider, DEFAULT_MODEL)
    valid_models = [m["id"] for m in PROVIDER_MODELS[provider]]
    if model not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model for {provider}. Valid: {valid_models}")

    extra_json = json.dumps(body.extra_config) if body.extra_config is not None else None

    async with get_session() as session:
        config = await crud.set_agent_config(session, workspace_id, at, model, extra_json, provider)
        try:
            provider_enum = ApiKeyProvider(provider)
        except ValueError:
            provider_enum = ApiKeyProvider.ANTHROPIC
        api_key = await crud.get_api_key(session, workspace_id, provider_enum)

    extra = {}
    if config.extra_config:
        try:
            extra = json.loads(config.extra_config)
        except (json.JSONDecodeError, TypeError):
            pass

    return AgentConfigResponse(
        agent_type=agent_type,
        provider=config.provider,
        model=config.model,
        active=api_key is not None,
        available_models=PROVIDER_MODELS.get(provider, PROVIDER_MODELS["anthropic"]),
        providers=[{"id": k, "name": k.title(), "models": v} for k, v in PROVIDER_MODELS.items()],
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
