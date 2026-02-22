"""FastAPI application entry point with lifespan management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import accounts, admin
from app.api.schemas.schemas import HealthResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.infrastructure.db.connection import create_pool, close_pool
from app.infrastructure.redis.client import create_redis_pool, close_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initializes and tears down infrastructure."""
    settings = get_settings()
    setup_logging(settings.app.log_level)

    logger.info("application_starting", service=settings.app.name)

    # ── Database pool ────────────────────────────────────
    app.state.db_pool = await create_pool(settings.postgres)

    # ── Redis (optional, non-blocking) ───────────────────
    app.state.redis_client = None
    try:
        app.state.redis_client = await create_redis_pool(settings.redis)
    except Exception:
        logger.warning("redis_unavailable_continuing_without_cache")

    logger.info("application_started")

    yield

    # ── Teardown ─────────────────────────────────────────
    if app.state.redis_client:
        await close_redis(app.state.redis_client)
    await close_pool(app.state.db_pool)
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Finance Microservice",
        description="High-load finance service for TikTok-like platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Register routers ─────────────────────────────────
    # app.include_router(admin.router)
    app.include_router(accounts.router)

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(service=settings.app.name)

    return app


app = create_app()
