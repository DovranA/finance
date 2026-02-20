"""RabbitMQ event consumer with deserialization and error handling."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable

import orjson
from aio_pika import IncomingMessage

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RewardEvent:
    """Deserialized reward event from RabbitMQ."""

    event_id: uuid.UUID
    actor_id: uuid.UUID
    content_id: uuid.UUID
    publisher_id: uuid.UUID
    action_code: str
    timestamp: datetime

    @classmethod
    def from_bytes(cls, body: bytes) -> RewardEvent:
        data = orjson.loads(body)
        return cls(
            event_id=uuid.UUID(data["event_id"]),
            actor_id=uuid.UUID(data["actor_id"]),
            content_id=uuid.UUID(data["content_id"]),
            publisher_id=uuid.UUID(data["publisher_id"]),
            action_code=data["action_code"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


EventHandler = Callable[[RewardEvent], Awaitable[None]]


async def consume_messages(
    message: IncomingMessage,
    handler: EventHandler,
) -> None:
    """Process a single incoming message with ack/nack."""
    async with message.process(requeue=True):
        try:
            event = RewardEvent.from_bytes(message.body)
            logger.info(
                "event_received",
                event_id=str(event.event_id),
                action_code=event.action_code,
                actor_id=str(event.actor_id),
            )
            await handler(event)
            logger.info(
                "event_processed",
                event_id=str(event.event_id),
            )
        except Exception:
            logger.exception(
                "event_processing_failed",
                body=message.body[:200],
            )
            raise
