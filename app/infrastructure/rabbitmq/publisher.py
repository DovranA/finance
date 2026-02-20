"""RabbitMQ outbound event publisher."""

from __future__ import annotations

from typing import Any

import orjson
from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractRobustExchange

from app.core.logging import get_logger

logger = get_logger(__name__)


class EventPublisher:
    """Publishes domain events to RabbitMQ exchange."""

    def __init__(self, exchange: AbstractRobustExchange) -> None:
        self._exchange = exchange

    async def publish(
        self,
        routing_key: str,
        payload: dict[str, Any],
    ) -> None:
        body = orjson.dumps(payload)
        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)
        logger.info(
            "event_published",
            routing_key=routing_key,
            payload_size=len(body),
        )
