"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maestro.api.agent_runs import router as agent_runs_router
from maestro.api.agents import router as agents_router
from maestro.api.auth import router as auth_router
from maestro.api.routes import router as api_router
from maestro.api.tasks import router as tasks_router
from maestro.api.workspaces import router as workspaces_router
from maestro.db.engine import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start DB on startup, stop on shutdown."""
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception:
        logger.exception("Failed to initialize database")

    from maestro.agent.plugin import init_plugins
    init_plugins()

    app.state.orchestrator = None

    yield

    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Maestro",
        description="Symphony-spec orchestration daemon for coding agents",
        version="0.1.0",
        lifespan=lifespan,
    )

    cors_origins = os.environ.get("MAESTRO_CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agent_runs_router)
    app.include_router(agents_router)
    app.include_router(auth_router)
    app.include_router(auth_router, prefix="/api")  # also serve at /api/auth/*
    app.include_router(api_router)
    app.include_router(tasks_router)
    app.include_router(workspaces_router)

    @app.get("/")
    async def root():
        return {
            "service": "maestro",
            "version": "0.1.0",
            "status": "ok",
        }

    return app


app = create_app()
