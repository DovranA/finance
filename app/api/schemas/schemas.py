"""Pydantic request/response schemas for the API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Admin: Economic Actions ──────────────────────────────────

class CreateActionRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100, examples=["LIKE"])
    description: str = Field("", max_length=500)


class CreateVersionRequest(BaseModel):
    publisher_reward: int = Field(..., ge=0, description="Amount in smallest currency unit")
    actor_reward: int = Field(..., ge=0)
    platform_fee: int = Field(..., ge=0)
    treasury_cut: int = Field(..., ge=0)


class ActivateVersionRequest(BaseModel):
    version_id: uuid.UUID


class ActionResponse(BaseModel):
    id: uuid.UUID
    code: str
    description: str
    is_active: bool
    created_at: datetime


class VersionResponse(BaseModel):
    id: uuid.UUID
    version: int
    publisher_reward: int
    actor_reward: int
    platform_fee: int
    treasury_cut: int
    is_active: bool
    active_from: datetime


class ActionWithVersionsResponse(BaseModel):
    id: str
    code: str
    description: str
    is_active: bool
    created_at: str
    versions: list[dict]


# ── Accounts ─────────────────────────────────────────────────

class BalanceResponse(BaseModel):
    user_id: str
    account_id: str | None = None
    balance: int
    currency: str
    found: bool
    cached: bool = False


# ── General ──────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "finance-service"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
