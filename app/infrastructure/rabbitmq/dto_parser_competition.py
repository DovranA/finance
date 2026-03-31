"""DTO parsers for competition messages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.event_schemas.competition_pb2 import UserCompetitionJoined


@dataclass(frozen=True)
class CompetitionEventDTO:
    """Data transfer object for competition events."""

    user_id: uuid.UUID
    in_competition: bool


def parse_competition_event(body: bytes) -> CompetitionEventDTO:
    """Parse competition event from protobuf UserCompetitionJoined payload."""
    payload = UserCompetitionJoined()
    payload.ParseFromString(body)

    if not payload.user_id:
        raise ValueError("competition message must contain user_id")

    return CompetitionEventDTO(
        user_id=uuid.UUID(payload.user_id),
        in_competition=True,
    )
