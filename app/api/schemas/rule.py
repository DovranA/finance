"""Request/response schemas for rule endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateRuleRequest(BaseModel):
    event_code: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    expired_at: datetime | None = None


class UpdateRuleRequest(BaseModel):
    event_code: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    priority: int | None = None
    is_active: bool | None = None
    expired_at: datetime | None = None


class RuleResponse(BaseModel):
    id: uuid.UUID
    event_code: str
    description: str | None
    conditions: dict[str, Any]
    actions: dict[str, Any]
    priority: int
    is_active: bool
    expired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    rules: list[RuleResponse]
    total: int
