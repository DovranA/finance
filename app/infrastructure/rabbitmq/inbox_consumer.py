"""RabbitMQ consumer that stores incoming actions into DB inbox table."""

from __future__ import annotations

import asyncio
from dishka import AsyncContainer
from aio_pika import IncomingMessage
from prometheus_client import start_http_server

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import AppMetrics, register_metrics
from app.infrastructure.rabbitmq.consumer import consume_messages
from app.infrastructure.rabbitmq.event_types import InboxEvent
from app.usecases.inbox_service import InboxService
from app.di import create_container
from app.infrastructure.rabbitmq.runner import ConsumerSpec, run_consumers

logger = get_logger(__name__)
_metrics: AppMetrics | None = None
_consumer_name = "inbox-rule-action-consumer"
_queue_name = ""


async def _inbox_message_handler(
    message: IncomingMessage,
    container: AsyncContainer,
) -> None:
    async def _handler(events: list[InboxEvent]) -> None:
        async with container() as scope:
            service = await scope.get(InboxService)
            await service.handle(events)

    await consume_messages(
        message,
        _handler,
        metrics=_metrics,
        consumer_name=_consumer_name,
        queue_name=_queue_name,
    )


def get_consumer_specs() -> list[ConsumerSpec]:
    settings = get_settings()
    rabbit = settings.rabbitmq
    queue = rabbit.queue_rewards
    return [
        ConsumerSpec(
            name="inbox-rule-action-consumer",
            exchange=rabbit.exchange,
            queue=queue,
            routing_key="#",
            handler=_inbox_message_handler,
            dead_letter_exchange="dlx",
            dead_letter_queue=f"{queue}.dlq",
            dead_letter_routing_key=f"{queue}.dlq",
        )
    ]


async def run_consumer(container: AsyncContainer) -> None:
    global _metrics, _queue_name
    settings = get_settings()

    if settings.app.enable_metrics and settings.app.metrics_port:
        start_http_server(settings.app.metrics_port)
        logger.info(
            "worker_metrics_server_started",
            worker="inbox_consumer",
            port=settings.app.metrics_port,
        )

    _metrics = await register_metrics()

    specs = get_consumer_specs()
    if specs:
        _queue_name = specs[0].queue
    await run_consumers(container, specs)


if __name__ == "__main__":
    asyncio.run(run_consumer(create_container()))
