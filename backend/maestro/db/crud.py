"""CRUD operations for tracker connections and pipeline records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maestro.db.encryption import decrypt_token, encrypt_token
from maestro.db.models import (
    AgentConfig,
    AgentType,
    ApiKey,
    ApiKeyProvider,
    PipelineStatus,
    TaskPipelineRecord,
    TrackerConnection,
    TrackerKind,
)


# ---------------------------------------------------------------------------
# Tracker Connections
# ---------------------------------------------------------------------------


async def create_connection(
    session: AsyncSession,
    kind: TrackerKind,
    name: str,
    project: str,
    token: str,
    endpoint: str = "",
    workspace_id: int | None = None,
) -> TrackerConnection:
    conn = TrackerConnection(
        workspace_id=workspace_id or 0,
        kind=kind,
        name=name,
        project=project,
        endpoint=endpoint,
        encrypted_token=encrypt_token(token),
    )
    session.add(conn)
    await session.commit()
    await session.refresh(conn)
    return conn


async def list_connections(session: AsyncSession) -> list[TrackerConnection]:
    result = await session.execute(select(TrackerConnection).order_by(TrackerConnection.id))
    return list(result.scalars().all())


async def get_connection(session: AsyncSession, connection_id: int) -> TrackerConnection | None:
    return await session.get(TrackerConnection, connection_id)


async def delete_connection(session: AsyncSession, connection_id: int) -> bool:
    conn = await session.get(TrackerConnection, connection_id)
    if not conn:
        return False
    await session.delete(conn)
    await session.commit()
    return True


def get_decrypted_token(conn: TrackerConnection) -> str:
    return decrypt_token(conn.encrypted_token)


# ---------------------------------------------------------------------------
# Task Pipeline
# ---------------------------------------------------------------------------


async def get_pipeline_record(
    session: AsyncSession, external_ref: str
) -> TaskPipelineRecord | None:
    result = await session.execute(
        select(TaskPipelineRecord).where(TaskPipelineRecord.external_ref == external_ref)
    )
    return result.scalar_one_or_none()


async def set_pipeline_status(
    session: AsyncSession,
    external_ref: str,
    tracker_connection_id: int,
    status: PipelineStatus,
) -> TaskPipelineRecord:
    record = await get_pipeline_record(session, external_ref)
    if record is None:
        record = TaskPipelineRecord(
            external_ref=external_ref,
            tracker_connection_id=tracker_connection_id,
            status=status,
        )
        session.add(record)
    else:
        record.status = status
    await session.commit()
    await session.refresh(record)
    return record


async def delete_pipeline_record(session: AsyncSession, external_ref: str) -> bool:
    record = await get_pipeline_record(session, external_ref)
    if not record:
        return False
    await session.delete(record)
    await session.commit()
    return True


async def list_pipeline_records(
    session: AsyncSession,
    status: PipelineStatus | None = None,
) -> list[TaskPipelineRecord]:
    stmt = select(TaskPipelineRecord).order_by(TaskPipelineRecord.updated_at.desc())
    if status is not None:
        stmt = stmt.where(TaskPipelineRecord.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


async def set_api_key(
    session: AsyncSession,
    workspace_id: int,
    provider: ApiKeyProvider,
    key: str,
) -> ApiKey:
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.workspace_id == workspace_id,
            ApiKey.provider == provider,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_key = encrypt_token(key)
        await session.commit()
        await session.refresh(existing)
        return existing
    else:
        api_key = ApiKey(
            workspace_id=workspace_id,
            provider=provider,
            encrypted_key=encrypt_token(key),
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return api_key


async def get_api_key(
    session: AsyncSession,
    workspace_id: int,
    provider: ApiKeyProvider,
) -> ApiKey | None:
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.workspace_id == workspace_id,
            ApiKey.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def delete_api_key(
    session: AsyncSession,
    workspace_id: int,
    provider: ApiKeyProvider,
) -> bool:
    api_key = await get_api_key(session, workspace_id, provider)
    if not api_key:
        return False
    await session.delete(api_key)
    await session.commit()
    return True


# ---------------------------------------------------------------------------
# Agent Config
# ---------------------------------------------------------------------------


async def get_agent_config(
    session: AsyncSession,
    workspace_id: int,
    agent_type: AgentType,
) -> AgentConfig | None:
    result = await session.execute(
        select(AgentConfig).where(
            AgentConfig.workspace_id == workspace_id,
            AgentConfig.agent_type == agent_type,
        )
    )
    return result.scalar_one_or_none()


async def set_agent_config(
    session: AsyncSession,
    workspace_id: int,
    agent_type: AgentType,
    model: str,
    extra_config: str | None = None,
) -> AgentConfig:
    result = await session.execute(
        select(AgentConfig).where(
            AgentConfig.workspace_id == workspace_id,
            AgentConfig.agent_type == agent_type,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.model = model
        if extra_config is not None:
            existing.extra_config = extra_config
        await session.commit()
        await session.refresh(existing)
        return existing
    else:
        config = AgentConfig(
            workspace_id=workspace_id,
            agent_type=agent_type,
            model=model,
            extra_config=extra_config or "{}",
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
        return config
