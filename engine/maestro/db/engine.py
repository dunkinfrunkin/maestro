"""Database engine and session management."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        url = url.replace("postgres://", "postgresql+asyncpg://")
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

    _engine = create_async_engine(
        get_database_url(),
        echo=False,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=600,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    import sqlalchemy as sa

    # Step 1: Add enum values (each in own transaction, idempotent)
    for val in ("GITLAB", "JIRA"):
        try:
            async with _engine.begin() as conn:
                await conn.execute(sa.text(
                    f"ALTER TYPE trackerkind ADD VALUE IF NOT EXISTS '{val}'"
                ))
        except Exception:
            pass

    try:
        async with _engine.begin() as conn:
            await conn.execute(sa.text(
                "ALTER TYPE apikeyprovider ADD VALUE IF NOT EXISTS 'OPENAI'"
            ))
    except Exception:
        pass

    for val in ("TODO", "IN_PROGRESS", "PENDING_APPROVAL", "APPROVED", "PROMOTE", "DONE", "FAILED", "HALTED"):
        try:
            async with _engine.begin() as conn:
                await conn.execute(sa.text(
                    f"ALTER TYPE pipelinestatus ADD VALUE IF NOT EXISTS '{val}'"
                ))
        except Exception:
            pass

    try:
        async with _engine.begin() as conn:
            await conn.execute(sa.text(
                "ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'REQUIREMENTS'"
            ))
    except Exception:
        pass

    # Step 2: Run DDL migrations with advisory lock (single connection holds lock + runs DDL)
    try:
        async with _engine.connect() as conn:
            # Use transaction-level advisory lock so it auto-releases
            result = await conn.execute(sa.text("SELECT pg_try_advisory_lock(73571)"))
            lock_acquired = result.scalar()

            if not lock_acquired:
                logger.info("Another process is running migrations, skipping")
                return

            try:
                await conn.run_sync(Base.metadata.create_all)
            except Exception:
                pass

            _ddl = [
                "ALTER TABLE tracker_connections ADD COLUMN IF NOT EXISTS email VARCHAR(255) NOT NULL DEFAULT ''",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS input_tokens INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS output_tokens INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE agent_configs ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NOT NULL DEFAULT 'anthropic'",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(255) NOT NULL DEFAULT ''",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS peak_memory_mb FLOAT NOT NULL DEFAULT 0.0",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS avg_cpu_percent FLOAT NOT NULL DEFAULT 0.0",
                "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS job_payload TEXT NOT NULL DEFAULT '{}'",
                "ALTER TABLE worker_heartbeats ADD COLUMN IF NOT EXISTS cpu_percent FLOAT NOT NULL DEFAULT 0.0",
                "ALTER TABLE worker_heartbeats ADD COLUMN IF NOT EXISTS memory_used_mb FLOAT NOT NULL DEFAULT 0.0",
                "ALTER TABLE worker_heartbeats ADD COLUMN IF NOT EXISTS memory_total_mb FLOAT NOT NULL DEFAULT 0.0",
                "ALTER TABLE worker_heartbeats ADD COLUMN IF NOT EXISTS cpu_count INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE worker_heartbeats ADD COLUMN IF NOT EXISTS estimated_capacity INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE task_pipeline ADD COLUMN IF NOT EXISTS last_comment_check_at TIMESTAMPTZ",
                "UPDATE agent_configs SET model = 'sonnet' WHERE model = 'claude-sonnet-4-6'",
                "UPDATE agent_configs SET model = 'opus' WHERE model = 'claude-opus-4-6'",
            ]
            for stmt in _ddl:
                try:
                    await conn.execute(sa.text(stmt))
                except Exception:
                    pass

            await conn.execute(sa.text("SELECT pg_advisory_unlock(73571)"))
            await conn.commit()
    except Exception as e:
        logger.warning("Migration error (non-fatal): %s", e)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def get_session():
    """Get a database session as an async context manager. Always closes on exit."""
    assert _session_factory is not None, "Database not initialized"
    session = _session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
