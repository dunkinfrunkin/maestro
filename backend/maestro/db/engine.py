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

    async with _engine.begin() as conn:
        # Add new enum values if they don't exist (postgres won't do this automatically)
        for val in ("GITLAB", "JIRA"):
            await conn.execute(
                __import__("sqlalchemy").text(
                    f"ALTER TYPE trackerkind ADD VALUE IF NOT EXISTS '{val}'"
                )
            )
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_session() -> AsyncSession:
    assert _session_factory is not None, "Database not initialized"
    return _session_factory()
