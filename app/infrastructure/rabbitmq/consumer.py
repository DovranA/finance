"""RabbitMQ event consumer with deserialization and error handling."""

from __future__ import annotations

import uuid
from typing import Awaitable, Callable

from aio_pika import IncomingMessage

from app.core.logging import get_logger
from app.infrastructure.rabbitmq.dto_parser import parse_user_engaged_list
from app.infrastructure.rabbitmq.event_mapper import (
    map_user_engaged_list_to_inbox_events,
)
from app.infrastructure.rabbitmq.event_types import InboxEvent

logger = get_logger(__name__)


def parse_inbox_events(body: bytes) -> list[InboxEvent]:
    dto = parse_user_engaged_list(body)
    return map_user_engaged_list_to_inbox_events(dto)


EventHandler = Callable[[list[InboxEvent]], Awaitable[None]]


async def consume_messages(
    message: IncomingMessage,
    handler: EventHandler,
) -> None:
    """Process a single incoming message with ack/nack."""
    async with message.process(requeue=False):
        try:
            events = parse_inbox_events(message.body)
            logger.info(
                "event_received",
                parsed_events=len(events),
            )
            await handler(events)
            logger.info(
                "event_processed",
                parsed_events=len(events),
            )
        except Exception:
            logger.exception(
                "event_processing_failed",
                body=message.body[:200],
            )
            raise
