"""RabbitMQ event consumer with deserialization and error handling."""

from __future__ import annotations

import time
from typing import Awaitable, Callable

from aio_pika import IncomingMessage

from app.core.logging import get_logger
from app.core.metrics import AppMetrics
from app.infrastructure.rabbitmq.dto_parser import (
    parse_user_deleted_json,
    parse_user_engaged_list,
    parse_user_engaged_list_json,
)
from app.infrastructure.rabbitmq.event_mapper import (
    map_user_deleted_to_inbox_events,
    map_user_engaged_list_to_inbox_events,
)
from app.infrastructure.rabbitmq.event_types import InboxEvent

logger = get_logger(__name__)


def parse_inbox_events(body: bytes) -> list[InboxEvent]:
    try:
        dto = parse_user_engaged_list(body)
    except Exception:
        try:
            dto = parse_user_engaged_list_json(body)
            return map_user_engaged_list_to_inbox_events(dto)
        except Exception:
            deleted_dto = parse_user_deleted_json(body)
            return map_user_deleted_to_inbox_events(deleted_dto)
    return map_user_engaged_list_to_inbox_events(dto)


EventHandler = Callable[[list[InboxEvent]], Awaitable[None]]


async def consume_messages(
    message: IncomingMessage,
    handler: EventHandler,
    metrics: AppMetrics | None = None,
    consumer_name: str = "unknown",
    queue_name: str = "unknown",
) -> None:
    """Process a single incoming message with ack/nack."""
    started_at = time.perf_counter()
    async with message.process(requeue=False):
        try:
            events = parse_inbox_events(message.body)
        except Exception as exc:
            if metrics is not None:
                metrics.inc_rabbitmq_message(consumer_name, queue_name, "skipped")
            logger.warning(
                "event_skipped_invalid_payload",
                reason=str(exc),
                body=message.body[:200],
            )
            return

        try:
            logger.info(
                "event_received",
                parsed_events=len(events),
            )
            if metrics is not None:
                metrics.inc_rabbitmq_message(consumer_name, queue_name, "received")
                for event in events:
                    metrics.inc_inbox_events("received", event.event_code)

            await handler(events)

            if metrics is not None:
                metrics.inc_rabbitmq_message(consumer_name, queue_name, "processed")
                for event in events:
                    metrics.inc_inbox_events("processed", event.event_code)

            logger.info(
                "event_processed",
                parsed_events=len(events),
            )
        except Exception:
            if metrics is not None:
                metrics.inc_rabbitmq_message(consumer_name, queue_name, "failed")
            logger.exception(
                "event_processing_failed",
                body=message.body[:200],
            )
            raise
        finally:
            if metrics is not None:
                metrics.observe_rabbitmq_processing(
                    consumer=consumer_name,
                    queue=queue_name,
                    duration_seconds=time.perf_counter() - started_at,
                )
