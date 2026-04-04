"""Database engine and session management."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    # Support DATABASE_URL (like Kit) or individual vars
    url = os.environ.get("DATABASE_URL", "")
    if url:
        # Convert postgres:// or postgresql:// to asyncpg driver
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        url = url.replace("postgres://", "postgresql+asyncpg://")
        # Strip sslmode param if present (asyncpg doesn't use it)
        if "?" in url:
            base, params = url.split("?", 1)
            params = "&".join(p for p in params.split("&") if not p.startswith("sslmode="))
            url = f"{base}?{params}" if params else base
        return url
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "maestro")
    user = os.environ.get("POSTGRES_USER", "maestro")
    password = os.environ.get("POSTGRES_PASSWORD", "maestro")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def init_db() -> None:
    """Initialize the database engine and create tables."""
    global _engine, _session_factory
    from maestro.db.models import Base

    _engine = create_async_engine(get_database_url(), echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    import sqlalchemy as sa

    # Step 1: Add enum values for existing DBs (must be outside the main DDL transaction
    # because asyncpg aborts the whole transaction on any error)
    try:
        async with _engine.begin() as conn:
            for val in ("GITLAB", "JIRA"):
                await conn.execute(sa.text(
                    f"ALTER TYPE trackerkind ADD VALUE IF NOT EXISTS '{val}'"
                ))
    except Exception:
        pass  # fresh DB — type doesn't exist yet, create_all will handle it

    try:
        async with _engine.begin() as conn:
            await conn.execute(sa.text(
                "ALTER TYPE apikeyprovider ADD VALUE IF NOT EXISTS 'OPENAI'"
            ))
    except Exception:
        pass  # fresh DB — create_all will handle it

    # Step 2: Create tables + run migrations
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(sa.text(
            "ALTER TABLE tracker_connections ADD COLUMN IF NOT EXISTS email VARCHAR(255) NOT NULL DEFAULT ''"
        ))
        # Add token tracking columns to agent_runs
        await conn.execute(sa.text(
            "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS input_tokens INTEGER NOT NULL DEFAULT 0"
        ))
        await conn.execute(sa.text(
            "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS output_tokens INTEGER NOT NULL DEFAULT 0"
        ))
        # Migrate old model IDs to CLI aliases
        await conn.execute(sa.text(
            "UPDATE agent_configs SET model = 'sonnet' WHERE model = 'claude-sonnet-4-6'"
        ))
        await conn.execute(sa.text(
            "UPDATE agent_configs SET model = 'opus' WHERE model = 'claude-opus-4-6'"
        ))


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session() -> AsyncSession:
    assert _session_factory is not None, "Database not initialized"
    return _session_factory()
