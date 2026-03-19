"""Request/response schemas for rule endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class RuleCondition(BaseModel):
    """Typed representation of a rule's conditions JSONB."""

    min_balance: Optional[int] = None
    role_required: Optional[list[str]] = None
    one_time_only: Optional[bool] = None
    daily_limit: Optional[int] = None
    cooldown_days: Optional[int] = None
    required_metadata: Optional[list[str]] = None
    idempotency_pattern: Optional[str] = None


class RuleAction(BaseModel):
    """Typed representation of a rule's actions JSONB."""

    direction: int = 1  # 1 = credit, -1 = debit
    amount: int = 0
    reward: int | None = None
    currency: str = "TMT"
    target_users: list[str] | None = None
    target_amounts: dict[str, int] | None = None


class RuleDescriptionI18n(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str | None = None
    ru: str | None = None
    tk: str | None = None


class CreateRuleRequest(BaseModel):
    event_code: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    description_i18n: RuleDescriptionI18n | None = None
    conditions: RuleCondition = Field(default_factory=dict)
    actions: RuleAction = Field(default_factory=dict)
    priority: int = 0
    expired_at: datetime | None = None


class UpdateRuleRequest(BaseModel):
    event_code: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    description_i18n: RuleDescriptionI18n | None = None
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    priority: int | None = None
    is_active: bool | None = None
    expired_at: datetime | None = None


class RuleResponse(BaseModel):
    id: uuid.UUID
    event_code: str
    description: str | None
    description_i18n: RuleDescriptionI18n | None = None
    localized_description: str | None = None
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


RuleLang = Literal["en", "ru", "tk"]


class ApplyRuleRequest(BaseModel):
    event_code: str = Field(min_length=1)
    user_id: uuid.UUID
    event_id: uuid.UUID | None = uuid.uuid4()
    role: str = "simple"
    metadata: dict[str, Any] | None = Field(default_factory=dict)


class BatchApplyRuleItem(BaseModel):
    user_id: uuid.UUID
    event_id: uuid.UUID | None = None
    role: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchApplyRuleRequest(BaseModel):
    event_code: str = Field(min_length=1)
    items: list[BatchApplyRuleItem] = Field(min_length=1)


class BatchApplyRuleResult(BaseModel):
    user_id: str
    applied: bool
    applied_rule: dict[str, Any] | None = None
    error: str | None = None


class BatchApplyRuleResponse(BaseModel):
    event_code: str
    total: int
    applied: int
    failed: int
    results: list[BatchApplyRuleResult]
