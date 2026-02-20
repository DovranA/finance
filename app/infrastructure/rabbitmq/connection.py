"""RabbitMQ connection management using aio-pika."""

from __future__ import annotations

import aio_pika
from aio_pika import RobustConnection, RobustChannel
from aio_pika.abc import AbstractRobustExchange

from app.core.config import RabbitMQSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_connection(settings: RabbitMQSettings) -> RobustConnection:
    """Create a robust (auto-reconnecting) RabbitMQ connection."""
    connection = await aio_pika.connect_robust(settings.url)
    logger.info(
        "rabbitmq_connected",
        host=settings.host,
        port=settings.port,
        vhost=settings.vhost,
    )
    return connection


async def create_channel(
    connection: RobustConnection,
    prefetch_count: int = 100,
) -> RobustChannel:
    """Create a channel with QoS prefetch."""
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=prefetch_count)
    return channel


async def declare_exchange(
    channel: RobustChannel,
    exchange_name: str,
) -> AbstractRobustExchange:
    """Declare a durable topic exchange."""
    exchange = await channel.declare_exchange(
        exchange_name,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    logger.info("rabbitmq_exchange_declared", exchange=exchange_name)
    return exchange


async def declare_queue(
    channel: RobustChannel,
    queue_name: str,
    exchange: AbstractRobustExchange,
    routing_key: str = "#",
) -> aio_pika.abc.AbstractRobustQueue:
    """Declare a durable queue and bind it to the exchange."""
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key=routing_key)
    logger.info(
        "rabbitmq_queue_declared",
        queue=queue_name,
        routing_key=routing_key,
    )
    return queue
