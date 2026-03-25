"""User domain model resolved from user-management service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class User:
    id: uuid.UUID
    username: str
    fullname: str | None
    is_following: bool
    role: str
