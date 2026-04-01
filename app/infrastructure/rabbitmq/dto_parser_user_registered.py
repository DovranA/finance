"""DTO parser for user registered protobuf messages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.event_schemas.user_pb2 import UserRegistered


@dataclass(frozen=True)
class UserRegisteredDTO:
    """Transport DTO for user registration event."""

    user_id: uuid.UUID
    role: str | None


def parse_user_registered_event(body: bytes) -> UserRegisteredDTO:
    """Parse protobuf UserRegistered message."""
    payload = UserRegistered()
    payload.ParseFromString(body)

    if not payload.user_id:
        raise ValueError("UserRegistered.user_id is required")

    try:
        user_id = uuid.UUID(payload.user_id)
    except ValueError as exc:
        raise ValueError("UserRegistered.user_id must be UUID") from exc

    role = payload.role.strip() if payload.role else None
    return UserRegisteredDTO(user_id=user_id, role=role)
