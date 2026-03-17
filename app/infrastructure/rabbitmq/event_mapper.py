"""Mapping from transport DTOs to inbox domain events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.infrastructure.rabbitmq.dto_parser import UserEngagedListDTO
from app.infrastructure.rabbitmq.event_types import InboxEvent


def map_user_engaged_list_to_inbox_events(
    dto: UserEngagedListDTO,
) -> list[InboxEvent]:
    try:
        actor_id = uuid.UUID(dto.user_id)
    except ValueError as exc:
        raise ValueError("UserEngagedList.user_id must be a UUID") from exc

    trace_id = dto.header.trace_id or str(uuid.uuid4())
    timestamp = dto.header.timestamp_iso or datetime.now(timezone.utc).isoformat()

    events: list[InboxEvent] = []
    for post in dto.post_list:
        try:
            author_id = uuid.UUID(post.author_id)
        except ValueError as exc:
            raise ValueError("Event.author_id must be a UUID") from exc

        for code in post.event_codes:
            unique_key = (
                f"{trace_id}:{dto.user_id}:{post.post_id}:{post.author_id}:{code}"
            )
            events.append(
                InboxEvent(
                    event_id=uuid.uuid5(uuid.NAMESPACE_URL, unique_key),
                    event_code=code,
                    user_id=author_id,
                    role=post.role or dto.role or None,
                    metadata={
                        "actor_id": str(actor_id),
                        "author_id": str(author_id),
                        "post_id": post.post_id,
                        "view_percentage": int(post.view_percentage),
                        "trace_id": trace_id,
                        "origin": dto.header.origin,
                        "type": dto.header.event_type,
                        "timestamp": timestamp,
                    },
                )
            )

    return events
