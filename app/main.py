"""FastAPI application entry point with Dishka DI container."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dishka.integrations.fastapi import setup_dishka

from app.api.routes import accounts
from app.api.routes import rule
from app.api.schemas.common import HealthResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.di import create_container
from app.domain.exceptions import (
    AccountInactive,
    AccountNotFound,
    CurrencyMismatch,
    DomainError,
    DuplicateOperation,
    InsufficientFunds,
    RuleAlreadyExists,
)
from app.usecases.rule_crud import RuleNotFound

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
    app.include_router(accounts.router)
    app.include_router(rule.router)

    # ── Exception handlers ───────────────────────────────
    @app.exception_handler(AccountNotFound)
    async def account_not_found_handler(request: Request, exc: AccountNotFound):
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(RuleNotFound)
    async def rule_not_found_handler(request: Request, exc: RuleNotFound):
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(RuleAlreadyExists)
    async def rule_already_exists_handler(request: Request, exc: RuleAlreadyExists):
        return JSONResponse(status_code=409, content={"error": str(exc)})

    @app.exception_handler(InsufficientFunds)
    async def insufficient_funds_handler(request: Request, exc: InsufficientFunds):
        return JSONResponse(status_code=422, content={"error": str(exc)})

    @app.exception_handler(DuplicateOperation)
    async def duplicate_handler(request: Request, exc: DuplicateOperation):
        return JSONResponse(status_code=409, content={"error": str(exc)})

    @app.exception_handler(AccountInactive)
    async def inactive_handler(request: Request, exc: AccountInactive):
        return JSONResponse(status_code=422, content={"error": str(exc)})

    @app.exception_handler(CurrencyMismatch)
    async def currency_handler(request: Request, exc: CurrencyMismatch):
        return JSONResponse(status_code=422, content={"error": str(exc)})

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    # ── Health endpoint ──────────────────────────────────
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(service=settings.app.name)

    return app


app = create_app()
