"""FastAPI application entry point with Dishka DI container."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from asyncpg import Pool
from dishka.integrations.fastapi import setup_dishka
from prometheus_client import make_asgi_app

from app.api.v0 import router as router_v0

from app.api.v0.schemas.common import HealthResponse
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.metrics import register_metrics, AppMetrics
from app.di import create_container
from app.grpc_server import create_grpc_server
from app.infrastructure.rabbitmq.inbox_consumer import (
    run_consumer as run_inbox_consumer,
)
from app.infrastructure.rabbitmq.competition_consumer import (
    run_consumer as run_competition_consumer,
)
from app.infrastructure.rabbitmq.user_registered_consumer import (
    run_consumer as run_user_registered_consumer,
)
from app.domain.exceptions import (
    AccountInactive,
    AccountNotFound,
    AuthError,
    CurrencyMismatch,
    DomainError,
    DuplicateOperation,
    InsufficientFunds,
    JwtConfigurationError,
    JwtValidationError,
    RuleAlreadyExists,
)
from app.usecases.rule_crud import RuleNotFound

logger = get_logger(__name__)


def _request_path(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


async def _collect_db_metrics(
    container,
    metrics: AppMetrics,
    interval_seconds: float,
) -> None:
    while True:
        try:
            async with container() as request_scope:
                pool = await request_scope.get(Pool)
                await metrics.record_db_stats(pool)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("db_metrics_collection_failed", error=str(exc))

        await asyncio.sleep(interval_seconds)


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
        swagger_ui_parameters={"persistAuthorization": True},
    )

    if settings.app.enable_metrics:
        app.mount("/metrics", make_asgi_app())

        @app.middleware("http")
        async def prometheus_http_metrics(request: Request, call_next):
            metrics = app.state.metrics
            started_at = time.perf_counter()

            try:
                response = await call_next(request)
            except Exception:
                duration = time.perf_counter() - started_at
                path = _request_path(request)
                metrics.inc_request(path, request.method, "500")
                metrics.observe_latency(path, request.method, "500", duration)
                raise

            status_code = str(response.status_code)
            duration = time.perf_counter() - started_at
            path = _request_path(request)
            metrics.inc_request(path, request.method, status_code)
            metrics.observe_latency(path, request.method, status_code, duration)
            return response

    # ── Dishka DI container ──────────────────────────────
    container = create_container()
    setup_dishka(container, app)
    app.state.container = container
    # ── Register routers ─────────────────────────────────
    app.include_router(router_v0, prefix="/api")

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

    @app.exception_handler(JwtValidationError)
    async def jwt_validation_error_handler(request: Request, exc: JwtValidationError):
        return JSONResponse(
            status_code=401,
            content={"error": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(JwtConfigurationError)
    async def jwt_configuration_error_handler(
        request: Request,
        exc: JwtConfigurationError,
    ):
        return JSONResponse(status_code=500, content={"error": str(exc)})

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        return JSONResponse(status_code=401, content={"error": str(exc)})

    # ── Health endpoint ──────────────────────────────────
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        return HealthResponse(service=settings.app.name)

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.db_metrics_task = None
    if settings.app.enable_metrics:
        app.state.metrics = await register_metrics()

    # ── STARTUP ─────────────────────────────

    # gRPC server
    app.state.grpc_server = await create_grpc_server(
        container=app.state.container,
        host=settings.app.host,
        port=50051,
    )
    await app.state.grpc_server.start()
    logger.info("grpc_server_started")

    # RabbitMQ consumers
    app.state.inbox_consumer_task = None
    app.state.competition_consumer_task = None
    app.state.user_registered_consumer_task = None
    logger.info(
        "inbox_consumer_toggle",
        enabled=settings.app.enable_inbox_consumer,
    )
    if settings.app.enable_inbox_consumer:
        app.state.inbox_consumer_task = asyncio.create_task(
            run_inbox_consumer(app.state.container),
            name="inbox_consumer",
        )
        app.state.inbox_consumer_task.add_done_callback(
            lambda t: _log_task_result("inbox_consumer", t)
        )
        logger.info("inbox_consumer_started")

    logger.info(
        "competition_consumer_toggle",
        enabled=settings.app.enable_competition_consumer,
    )
    if settings.app.enable_competition_consumer:
        app.state.competition_consumer_task = asyncio.create_task(
            run_competition_consumer(app.state.container),
            name="competition_consumer",
        )
        app.state.competition_consumer_task.add_done_callback(
            lambda t: _log_task_result("competition_consumer", t)
        )
        logger.info("competition_consumer_started")

    logger.info(
        "user_registered_consumer_toggle",
        enabled=settings.app.enable_user_registered_consumer,
    )
    if settings.app.enable_user_registered_consumer:
        app.state.user_registered_consumer_task = asyncio.create_task(
            run_user_registered_consumer(app.state.container),
            name="user_registered_consumer",
        )
        app.state.user_registered_consumer_task.add_done_callback(
            lambda t: _log_task_result("user_registered_consumer", t)
        )
        logger.info("user_registered_consumer_started")

    if settings.app.enable_metrics:
        app.state.db_metrics_task = asyncio.create_task(
            _collect_db_metrics(
                container=app.state.container,
                metrics=app.state.metrics,
                interval_seconds=settings.app.metrics_db_interval_seconds,
            ),
            name="db_metrics_collector",
        )
        app.state.db_metrics_task.add_done_callback(
            lambda t: _log_task_result("db_metrics_collector", t)
        )

    yield  # ← приложение работает

    # ── SHUTDOWN ────────────────────────────

    # stop consumers
    task = getattr(app.state, "inbox_consumer_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    competition_task = getattr(app.state, "competition_consumer_task", None)
    if competition_task:
        competition_task.cancel()
        try:
            await competition_task
        except asyncio.CancelledError:
            pass

    user_registered_task = getattr(app.state, "user_registered_consumer_task", None)
    if user_registered_task:
        user_registered_task.cancel()
        try:
            await user_registered_task
        except asyncio.CancelledError:
            pass

    metrics_task = getattr(app.state, "db_metrics_task", None)
    if metrics_task:
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass

    # stop gRPC
    server = getattr(app.state, "grpc_server", None)
    if server:
        await server.stop(grace=5)


app = create_app()
