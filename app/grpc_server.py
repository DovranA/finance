"""Async gRPC server entry point for finance services."""

from __future__ import annotations

import uuid

from dishka import AsyncContainer
import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from app.core.logging import get_logger

from app.usecases.get_balance import GetBalanceUseCase

from app.domain.event_schemas import finance_pb2, finance_pb2_grpc

logger = get_logger(__name__)


class BalanceService(finance_pb2_grpc.BalanceServiceServicer):
    """gRPC сервис через DI container (REQUEST scope)."""

    def __init__(self, container: AsyncContainer):
        self._container = container

    async def GetBalance(
        self, request: finance_pb2.GetBalanceRequest, context: grpc.aio.ServicerContext
    ) -> finance_pb2.GetBalanceResponse:
        async with self._container() as request_container:
            uc: GetBalanceUseCase = await request_container.get(GetBalanceUseCase)

            try:
                user_id = uuid.UUID(request.user_id)
            except ValueError:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "invalid user_id")

            result = await uc.execute(user_id=user_id)

            return finance_pb2.GetBalanceResponse(
                user_id=result["user_id"],
                account_id=result.get("account_id") or "",
                balance=int(result["balance"]),
                currency=str(result["currency"]),
                cached=bool(result.get("cached", False)),
            )


async def create_grpc_server(container, host: str, port: int) -> grpc.aio.Server:
    """Создаёт gRPC сервер (без запуска)."""

    server = grpc.aio.server()

    # health check
    health_servicer = health.HealthServicer(
        experimental_non_blocking=True,
        experimental_thread_pool=None,
    )

    # регистрируем сервисы
    finance_pb2_grpc.add_BalanceServiceServicer_to_server(
        BalanceService(container),
        server,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    server.add_insecure_port(f"{host}:{port}")

    # health статусы
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set(
        "finance.BalanceService",
        health_pb2.HealthCheckResponse.SERVING,
    )

    return server
