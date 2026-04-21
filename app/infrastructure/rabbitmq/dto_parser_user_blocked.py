"""DTO parser for user deleted protobuf messages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.event_schemas.user_pb2 import UserReported


@dataclass(frozen=True)
class UserBlockedDTO:
    """Transport DTO for user registration event."""

    user_id: uuid.UUID
    is_blocked: bool


def parse_user_blocked_event(body: bytes) -> UserBlockedDTO:
    """Parse protobuf UserBlocked message."""
    payload = UserReported()
    payload.ParseFromString(body)

    if not payload.user_id:
        raise ValueError("UserBlocked.user_id is required")

    try:
        user_id = uuid.UUID(payload.user_id)
    except ValueError as exc:
        raise ValueError("UserBlocked.user_id must be UUID") from exc

    is_blocked = payload.is_blocked if payload.is_blocked is not None else False
    return UserBlockedDTO(user_id=user_id, is_blocked=is_blocked)
