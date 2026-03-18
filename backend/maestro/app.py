"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maestro.api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Maestro",
        description="Symphony-spec orchestration daemon for coding agents",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/")
    async def root():
        return {"service": "maestro", "version": "0.1.0", "status": "ok"}

    return app


app = create_app()
