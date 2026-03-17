"""RabbitMQ consumer that stores incoming actions into DB inbox table."""

from __future__ import annotations

import asyncio
from dishka import AsyncContainer
from aio_pika import IncomingMessage

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.rabbitmq.consumer import consume_messages
from app.infrastructure.rabbitmq.event_types import InboxEvent
from app.usecases.inbox_service import InboxService
from app.di import create_container
from app.infrastructure.rabbitmq.runner import ConsumerSpec, run_consumers

logger = get_logger(__name__)


async def _inbox_message_handler(
    message: IncomingMessage,
    container: AsyncContainer,
) -> None:
    async def _handler(events: list[InboxEvent]) -> None:
        async with container() as scope:
            service = await scope.get(InboxService)
            await service.handle(events)

    await consume_messages(message, _handler)


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
    await run_consumers(container, get_consumer_specs())


if __name__ == "__main__":
    asyncio.run(run_consumer(create_container()))
