"""RabbitMQ consumer for UserRegistered events."""

from __future__ import annotations

import asyncio

from aio_pika import IncomingMessage
from dishka import AsyncContainer
from prometheus_client import start_http_server

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import AppMetrics, register_metrics
from app.di import create_container
from app.infrastructure.rabbitmq.dto_parser_user_registered import (
    parse_user_registered_event,
)
from app.infrastructure.rabbitmq.runner import ConsumerSpec, run_consumers
from app.usecases.register_user import RegisterUserUseCase

logger = get_logger(__name__)
_metrics: AppMetrics | None = None
_consumer_name = "user-registered-consumer"
_queue_name = ""


async def _user_registered_message_handler(
    message: IncomingMessage,
    container: AsyncContainer,
) -> None:
    import time

    started_at = time.perf_counter()
    async with message.process(requeue=False):
        try:
            event = parse_user_registered_event(message.body)
            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "received")

            async with container() as scope:
                use_case = await scope.get(RegisterUserUseCase)
                result = await use_case.execute(
                    user_id=event.user_id,
                    role=event.role,
                    currency="TOKEN",
                )

            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "processed")

            logger.info(
                "user_registered_event_processed",
                user_id=str(event.user_id),
                created=result.get("created"),
                account_id=result.get("account_id"),
                duration_ms=(time.perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "failed")
            logger.error(
                "user_registered_event_failed",
                error=str(exc),
                exc_info=True,
            )
            raise


def get_consumer_specs() -> list[ConsumerSpec]:
    settings = get_settings()
    rabbit = settings.rabbitmq
    queue = rabbit.queue_user_registered
    return [
        ConsumerSpec(
            name=_consumer_name,
            exchange="user",
            queue=queue,
            routing_key="user.registered:update.finance",
            handler=_user_registered_message_handler,
        )
    ]


async def run_consumer(container: AsyncContainer) -> None:
    global _metrics, _queue_name
    settings = get_settings()

    if settings.app.enable_metrics and settings.app.metrics_port:
        start_http_server(settings.app.metrics_port)
        logger.info(
            "worker_metrics_server_started",
            worker="user_registered_consumer",
            port=settings.app.metrics_port,
        )

    _metrics = await register_metrics()
    specs = get_consumer_specs()
    if specs:
        _queue_name = specs[0].queue
    await run_consumers(container, specs)


if __name__ == "__main__":
    asyncio.run(run_consumer(create_container()))
