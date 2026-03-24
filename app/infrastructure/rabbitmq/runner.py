"""Multi-consumer runner for RabbitMQ queues in a single process."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

from aio_pika import IncomingMessage
from dishka import AsyncContainer

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import register_metrics
from app.infrastructure.rabbitmq.connection import (
    create_channel,
    create_connection,
    declare_exchange,
    declare_queue,
)

logger = get_logger(__name__)


MessageHandler = Callable[[IncomingMessage, AsyncContainer], Awaitable[None]]


@dataclass(frozen=True)
class ConsumerSpec:
    name: str
    exchange: str
    queue: str
    routing_key: str
    handler: MessageHandler
    dead_letter_exchange: str = ""
    dead_letter_queue: str = ""
    dead_letter_routing_key: str = ""


async def run_consumers(container: AsyncContainer, specs: list[ConsumerSpec]) -> None:
    settings = get_settings()
    rabbit = settings.rabbitmq
    metrics = await register_metrics()

    connection = await create_connection(rabbit)
    channel = await create_channel(connection, prefetch_count=rabbit.prefetch_count)

    try:
        for spec in specs:
            exchange = await declare_exchange(channel, spec.exchange)

            queue_args: dict[str, str] | None = None
            if spec.dead_letter_exchange:
                await declare_exchange(channel, spec.dead_letter_exchange)
                await channel.declare_queue(spec.dead_letter_queue, durable=True)
                queue_args = {
                    "x-dead-letter-exchange": spec.dead_letter_exchange,
                    "x-dead-letter-routing-key": spec.dead_letter_routing_key,
                }

            await declare_queue(
                channel,
                spec.queue,
                exchange,
                routing_key=spec.routing_key,
                arguments=queue_args,
            )

            queue = await channel.get_queue(spec.queue)
            await queue.consume(lambda msg, h=spec.handler: h(msg, container))
            metrics.set_rabbitmq_consumer_up(spec.name, spec.queue, True)
            logger.info(
                "rabbitmq_consumer_registered",
                consumer=spec.name,
                queue=spec.queue,
                exchange=spec.exchange,
                routing_key=spec.routing_key,
            )

        await asyncio.Future()
    finally:
        for spec in specs:
            metrics.set_rabbitmq_consumer_up(spec.name, spec.queue, False)
        await channel.close()
        await connection.close()
