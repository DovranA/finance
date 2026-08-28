from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v0.routes.rule import apply_rule
from app.api.v0.schemas.rule import ApplyRuleRequest


@pytest.mark.asyncio
async def test_jwt_caller_identity_and_role_come_from_token_not_body():
    real_user = uuid.uuid4()
    spoofed_user = uuid.uuid4()
    uc = AsyncMock()
    uc.execute.return_value = {"status": "applied"}

    body = ApplyRuleRequest(
        user_id=spoofed_user, event_code="LIKE", role="official"
    )
    auth = {"sub": str(real_user), "role": "simple"}

    await apply_rule(uc, body, auth)

    _, kwargs = uc.execute.call_args
    assert kwargs["user_id"] == real_user
    assert kwargs["metadata"]["role"] == "simple"


@pytest.mark.asyncio
async def test_jwt_caller_cannot_use_dynamic_amount():
    uc = AsyncMock()
    body = ApplyRuleRequest(
        event_code="BONUS", metadata={"dynamic_amount": 999_999_999}
    )
    auth = {"sub": str(uuid.uuid4()), "role": "simple"}

    with pytest.raises(HTTPException) as exc_info:
        await apply_rule(uc, body, auth)

    assert exc_info.value.status_code == 403
    uc.execute.assert_not_called()


@pytest.mark.asyncio
async def test_service_caller_requires_explicit_user_id():
    uc = AsyncMock()
    body = ApplyRuleRequest(event_code="BONUS")
    auth: dict = {}  # api-key auth (or JWT disabled) carries no "sub"

    with pytest.raises(HTTPException) as exc_info:
        await apply_rule(uc, body, auth)

    assert exc_info.value.status_code == 422
    uc.execute.assert_not_called()


@pytest.mark.asyncio
async def test_service_caller_can_act_on_behalf_of_given_user():
    target_user = uuid.uuid4()
    uc = AsyncMock()
    uc.execute.return_value = {"status": "applied"}

    body = ApplyRuleRequest(
        user_id=target_user,
        event_code="BONUS",
        role="simple",
        metadata={"dynamic_amount": 42},
    )
    auth: dict = {}

    await apply_rule(uc, body, auth)

    _, kwargs = uc.execute.call_args
    assert kwargs["user_id"] == target_user
    assert kwargs["metadata"]["dynamic_amount"] == 42
