"""FastAPI application factory with orchestrator lifecycle."""

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
from maestro.config.loader import ConfigLoader
from maestro.db.engine import close_db, init_db
from maestro.orchestrator.engine import Orchestrator
from maestro.tracker.linear import LinearClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start DB + orchestrator on startup, stop on shutdown."""
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception:
        logger.exception("Failed to initialize database")

    # Initialize OIDC (if configured)
    from maestro.auth import init_oidc
    init_oidc()

    # Initialize plugin registry
    from maestro.agent.plugin import init_plugins
    init_plugins()

    workflow_path = os.environ.get("MAESTRO_WORKFLOW", "WORKFLOW.md")

    orchestrator = None
    tracker = None

    if os.path.exists(workflow_path):
        try:
            loader = ConfigLoader(workflow_path)
            loader.load()
            cfg = loader.config

            tracker = LinearClient(
                api_key=cfg.tracker.api_key,
                project_slug=cfg.tracker.project_slug,
                active_states=cfg.tracker.active_states,
                terminal_states=cfg.tracker.terminal_states,
                endpoint=cfg.tracker.endpoint,
            )

            orchestrator = Orchestrator(config_loader=loader, tracker=tracker)
            await orchestrator.start()
            logger.info("Orchestrator started with workflow: %s", workflow_path)
        except Exception:
            logger.exception("Failed to start orchestrator — running in API-only mode")
            orchestrator = None
    else:
        logger.warning("No WORKFLOW.md found at %s — running in API-only mode", workflow_path)

    app.state.orchestrator = orchestrator

    yield

    if orchestrator:
        await orchestrator.stop()
    if tracker:
        await tracker.close()
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
    app.include_router(api_router)
    app.include_router(tasks_router)
    app.include_router(workspaces_router)

    @app.get("/")
    async def root():
        return {
            "service": "maestro",
            "version": "0.1.0",
            "status": "ok",
            "orchestrator": app.state.orchestrator is not None,
        }

    return app


app = create_app()
