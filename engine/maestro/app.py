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
from maestro.api.statuses import router as statuses_router
from maestro.api.tasks import router as tasks_router
from maestro.api.workspaces import router as workspaces_router
from maestro.config.loader import ConfigLoader
from maestro.db.engine import close_db, init_db
from maestro.orchestrator.engine import Orchestrator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start DB + orchestrator on startup, stop on shutdown."""
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception:
        logger.exception("Failed to initialize database")

    from maestro.agents.plugin import init_plugins
    init_plugins()

    orchestrator = None
    try:
        loader = ConfigLoader()
        orchestrator = Orchestrator(config_loader=loader)
        await orchestrator.start()
    except Exception:
        logger.exception("Failed to start orchestrator")

    app.state.orchestrator = orchestrator

    yield

    if orchestrator:
        await orchestrator.stop()
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
    app.include_router(statuses_router)
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
