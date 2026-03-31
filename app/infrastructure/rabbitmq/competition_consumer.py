"""RabbitMQ consumer for managing competition participation."""

from __future__ import annotations

import asyncio

from aio_pika import IncomingMessage
from dishka import AsyncContainer
from prometheus_client import start_http_server

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import AppMetrics, register_metrics
from app.infrastructure.rabbitmq.dto_parser_competition import (
    parse_competition_event,
)
from app.usecases.set_balance import SetBalanceUseCase
from app.usecases.competition_service import CompetitionService
from app.di import create_container
from app.infrastructure.rabbitmq.runner import ConsumerSpec, run_consumers

logger = get_logger(__name__)
_metrics: AppMetrics | None = None
_consumer_name = "competition-consumer"
_queue_name = ""


async def _competition_message_handler(
    message: IncomingMessage,
    container: AsyncContainer,
) -> None:
    """Handle incoming competition events from RabbitMQ."""
    import time

    started_at = time.perf_counter()
    async with message.process(requeue=False):
        try:
            event = parse_competition_event(message.body)
            logger.info(
                "competition_event_received",
                user_id=str(event.user_id),
                in_competition=event.in_competition,
            )

            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "received")

            async with container() as scope:
                service = await scope.get(CompetitionService)
                await service.handle(event.user_id, event.in_competition)

                set_balance_uc = await scope.get(SetBalanceUseCase)
                await set_balance_uc.execute(
                    user_id=event.user_id,
                    new_balance=0,
                    currency="TOKEN",
                )
                logger.info(
                    "competition_user_balance_reset",
                    user_id=str(event.user_id),
                    new_balance=0,
                    currency="TOKEN",
                )

            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "processed")

            duration = time.perf_counter() - started_at
            logger.info(
                "competition_event_processed",
                duration_ms=duration * 1000,
                user_id=str(event.user_id),
            )
        except Exception as e:
            logger.error(
                "competition_message_processing_failed",
                error=str(e),
                exc_info=True,
            )
            if _metrics is not None:
                _metrics.inc_rabbitmq_message(_consumer_name, _queue_name, "failed")
            raise


def get_consumer_specs() -> list[ConsumerSpec]:
    """Get consumer specifications for competition events."""
    settings = get_settings()
    rabbit = settings.rabbitmq
    queue = rabbit.queue_competition
    return [
        ConsumerSpec(
            name="competition-consumer",
            exchange="user",
            queue=queue,
            routing_key="user-competition.joined:update.finance",
            handler=_competition_message_handler,
        )
    ]


async def run_consumer(container: AsyncContainer) -> None:
    global _metrics, _queue_name
    settings = get_settings()

    if settings.app.enable_metrics and settings.app.metrics_port:
        start_http_server(settings.app.metrics_port)
        logger.info(
            "worker_metrics_server_started",
            worker="competition_consumer",
            port=settings.app.metrics_port,
        )

    _metrics = await register_metrics()

    specs = get_consumer_specs()
    if specs:
        _queue_name = specs[0].queue
    await run_consumers(container, specs)


if __name__ == "__main__":
    """Run the competition consumer."""
    asyncio.run(run_consumer(create_container()))
