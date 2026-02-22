"""FastAPI application entry point with Dishka DI container."""

from __future__ import annotations

from fastapi import FastAPI
from dishka.integrations.fastapi import setup_dishka

from app.api.routes import accounts, admin
from app.api.schemas.schemas import HealthResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.di import create_container

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    setup_logging(settings.app.log_level)

    app = FastAPI(
        title="Finance Microservice",
        description="High-load finance service for TikTok-like platform",
        version="1.0.0",
    )

    # ── Dishka DI container ──────────────────────────────
    container = create_container()
    setup_dishka(container, app)

    # ── Register routers ─────────────────────────────────
    # app.include_router(admin.router)
    app.include_router(accounts.router)

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(service=settings.app.name)

    return app


app = create_app()
