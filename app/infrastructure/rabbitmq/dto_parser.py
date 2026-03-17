"""Transport-level protobuf parsing into plain DTO objects."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.event_schemas import finance_pb2


@dataclass(frozen=True)
class UserEventHeaderDTO:
    trace_id: str
    event_type: str
    origin: str
    timestamp_iso: str | None


@dataclass(frozen=True)
class UserPostEventDTO:
    event_codes: list[str]
    post_id: str
    author_id: str
    view_percentage: int
    role: str


@dataclass(frozen=True)
class UserEngagedListDTO:
    header: UserEventHeaderDTO
    user_id: str
    role: str
    post_list: list[UserPostEventDTO]


def parse_user_engaged_list(body: bytes) -> UserEngagedListDTO:
    payload = finance_pb2.UserEngagedList()
    payload.ParseFromString(body)

    timestamp_iso = None
    if payload.header.HasField("timestamp"):
        timestamp_iso = payload.header.timestamp.ToDatetime().isoformat()

    header = UserEventHeaderDTO(
        trace_id=payload.header.trace_id,
        event_type=payload.header.type,
        origin=payload.header.origin,
        timestamp_iso=timestamp_iso,
    )

    posts = [
        UserPostEventDTO(
            event_codes=list(item.event_code),
            post_id=item.post_id,
            author_id=item.author_id,
            view_percentage=int(item.view_percentage),
            role=item.role,
        )
        for item in payload.post_list
    ]

    return UserEngagedListDTO(
        header=header,
        user_id=payload.user_id,
        role=payload.role,
        post_list=posts,
    )
