"""FastAPI application entry point with Dishka DI container."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dishka.integrations.fastapi import setup_dishka

from app.api.routes import accounts
from app.api.routes import rule
from app.api.schemas.common import HealthResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.di import create_container
from app.grpc_server import create_grpc_server
from app.infrastructure.rabbitmq.inbox_consumer import run_consumer
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


def _log_task_result(task_name: str, task: asyncio.Task) -> None:
    """Log unhandled background task failures explicitly."""
    if task.cancelled():
        logger.info("background_task_cancelled", task=task_name)
        return

    exc = task.exception()
    if exc is not None:
        logger.exception(
            "background_task_failed",
            task=task_name,
            error=str(exc),
        )


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    setup_logging(settings.app.log_level)

    app = FastAPI(
        title="Finance Microservice",
        description="High-load finance service for TikTok-like platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Dishka DI container ──────────────────────────────
    container = create_container()
    setup_dishka(container, app)
    app.state.container = container
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # ── STARTUP ─────────────────────────────

    # gRPC server
    app.state.grpc_server = await create_grpc_server(
        container=app.state.container,
        host=settings.app.host,
        port=50051,
    )
    await app.state.grpc_server.start()
    logger.info("grpc_server_started")

    # RabbitMQ consumer
    app.state.inbox_consumer_task = None
    logger.info(
        "inbox_consumer_toggle",
        enabled=settings.app.enable_inbox_consumer,
    )
    if settings.app.enable_inbox_consumer:
        app.state.inbox_consumer_task = asyncio.create_task(
            run_consumer(app.state.container),
            name="inbox_consumer",
        )
        app.state.inbox_consumer_task.add_done_callback(
            lambda t: _log_task_result("inbox_consumer", t)
        )
        logger.info("inbox_consumer_started")

    yield  # ← приложение работает

    # ── SHUTDOWN ────────────────────────────

    # stop consumer
    task = getattr(app.state, "inbox_consumer_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # stop gRPC
    server = getattr(app.state, "grpc_server", None)
    if server:
        await server.stop(grace=5)


app = create_app()
