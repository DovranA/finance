from dataclasses import dataclass


@dataclass
class EventAction:
    """Defines the structure of an incoming event action from the event stream."""

    actor_id: str
    content_id: str
    action_code: str
    timestamp: str  # ISO 8601 format
