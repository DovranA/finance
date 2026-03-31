"""Transport-level protobuf parsing into plain DTO objects."""

from __future__ import annotations

from dataclasses import dataclass
import json

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


@dataclass(frozen=True)
class UserDeletedDTO:
    header: UserEventHeaderDTO
    user_id: str
    role: str


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
            role="simple",
        )
        for item in payload.post_list
    ]

    return UserEngagedListDTO(
        header=header,
        user_id=payload.user_id,
        role=payload.role,
        post_list=posts,
    )


def parse_user_engaged_list_json(body: bytes) -> UserEngagedListDTO:
    """Parse Debezium outbox JSON payload into transport DTO."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")

    header_raw = payload.get("header")
    if not isinstance(header_raw, dict):
        header_raw = {}

    posts_raw = payload.get("post_list")
    if not isinstance(posts_raw, list):
        raise ValueError("JSON payload must contain post_list array")

    header = UserEventHeaderDTO(
        trace_id=str(header_raw.get("trace_id", "")),
        event_type=str(header_raw.get("type", "")),
        origin=str(header_raw.get("origin", "")),
        timestamp_iso=(
            str(header_raw["timestamp"])
            if header_raw.get("timestamp") is not None
            else None
        ),
    )

    posts: list[UserPostEventDTO] = []
    for item in posts_raw:
        if not isinstance(item, dict):
            raise ValueError("post_list items must be objects")

        event_codes_raw = item.get("event_code", item.get("event_codes", []))
        if isinstance(event_codes_raw, str):
            event_codes = [event_codes_raw]
        elif isinstance(event_codes_raw, list):
            event_codes = [str(code) for code in event_codes_raw]
        else:
            raise ValueError("event_code must be string or array")

        posts.append(
            UserPostEventDTO(
                event_codes=event_codes,
                post_id=str(item.get("post_id", "")),
                author_id=str(item.get("author_id", "")),
                view_percentage=int(item.get("view_percentage", 0)),
                role=str(item.get("role", "simple")),
            )
        )

    return UserEngagedListDTO(
        header=header,
        user_id=str(payload.get("user_id", "")),
        role=str(payload.get("role", "")),
        post_list=posts,
    )


def parse_user_deleted_json(body: bytes) -> UserDeletedDTO:
    """Parse user-deleted event JSON payload into transport DTO."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise ValueError("invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")

    header_raw = payload.get("header")
    if not isinstance(header_raw, dict):
        header_raw = {}

    payload_type = str(payload.get("type", "")).strip().lower()
    payload_event_code = str(payload.get("event_code", "")).strip().lower()
    header_type = str(header_raw.get("type", "")).strip().lower()

    # Accept delete only when event type is explicitly declared.
    accepted_types = {"user.deleted", "user_deleted"}
    if not any(
        marker in accepted_types
        for marker in (payload_type, payload_event_code, header_type)
    ):
        raise ValueError("payload is not user deleted event")

    user_id = payload.get("user_id", payload.get("userId", ""))
    if not user_id:
        raise ValueError("JSON payload must contain user_id")

    header = UserEventHeaderDTO(
        trace_id=str(header_raw.get("trace_id", "")),
        event_type=(
            str(header_raw.get("type"))
            if header_raw.get("type")
            else (str(payload.get("type")) or "user.deleted")
        ),
        origin=str(header_raw.get("origin", "")),
        timestamp_iso=(
            str(header_raw["timestamp"])
            if header_raw.get("timestamp") is not None
            else None
        ),
    )

    return UserDeletedDTO(
        header=header,
        user_id=str(user_id),
        role=str(payload.get("role", "")),
    )
