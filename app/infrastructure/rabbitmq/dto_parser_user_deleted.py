"""DTO parser for user deleted protobuf messages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.event_schemas.user_pb2 import UserDeleted


@dataclass(frozen=True)
class UserDeletedDTO:
    """Transport DTO for user registration event."""

    user_id: uuid.UUID
    role: str | None


def parse_user_deleted_event(body: bytes) -> UserDeletedDTO:
    """Parse protobuf UserDeleted message."""
    payload = UserDeleted()
    payload.ParseFromString(body)

    if not payload.user_id:
        raise ValueError("UserDeleted.user_id is required")

    try:
        user_id = uuid.UUID(payload.user_id)
    except ValueError as exc:
        raise ValueError("UserDeleted.user_id must be UUID") from exc

    role = payload.role.strip() if payload.role else None
    return UserDeletedDTO(user_id=user_id, role=role)
