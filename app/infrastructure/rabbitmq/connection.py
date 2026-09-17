"""RabbitMQ connection management using aio-pika."""

from __future__ import annotations
from typing import Any

import aio_pika
from aio_pika import RobustConnection, RobustChannel
from aio_pika.abc import AbstractRobustExchange

from app.core.config import RabbitMQSettings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_connection(settings: RabbitMQSettings) -> RobustConnection:
    """Create a robust (auto-reconnecting) RabbitMQ connection.

    Tries each RABBITMQ_CLUSTER_ADDRS node in order, connecting to the first
    that accepts. aio-pika's robust reconnect then keeps retrying that same
    node — it doesn't fail over to another node if that one goes down after
    a successful connect.
    # ponytail: connect-time failover only; add per-node retry in the
    # reconnect loop if losing a node mid-run must also fail over.
    """
    last_exc: Exception | None = None
    for url in settings.urls:
        try:
            connection = await aio_pika.connect_robust(url)
        except Exception as exc:  # noqa: BLE001 — try the next node
            last_exc = exc
            logger.warning("rabbitmq_connect_failed", url=url, error=str(exc))
            continue
        logger.info("rabbitmq_connected", url=url, vhost=settings.vhost)
        return connection
    raise last_exc


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
    arguments: dict[str, Any] | None = None,
) -> aio_pika.abc.AbstractRobustQueue:
    """Declare a durable queue and bind it to the exchange."""
    queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments=arguments,
    )
    await queue.bind(exchange, routing_key=routing_key)
    logger.info(
        "rabbitmq_queue_declared",
        queue=queue_name,
        routing_key=routing_key,
    )
    return queue
