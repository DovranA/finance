from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.policies.validators.dynamic_amount import DynamicAmountValidator


@pytest.mark.asyncio
async def test_accepts_positive_integer(mock_conn):
    validator = DynamicAmountValidator()
    account = SimpleNamespace(id="account-1", balance=0)

    await validator.validate(
        True, account=account, metadata={"dynamic_amount": 10}, conn=mock_conn
    )


@pytest.mark.asyncio
async def test_rejects_negative_amount(mock_conn):
    validator = DynamicAmountValidator()
    account = SimpleNamespace(id="account-1", balance=0)

    with pytest.raises(ValueError, match="positive integer"):
        await validator.validate(
            True, account=account, metadata={"dynamic_amount": -50}, conn=mock_conn
        )


@pytest.mark.asyncio
async def test_rejects_non_integer_amount(mock_conn):
    validator = DynamicAmountValidator()
    account = SimpleNamespace(id="account-1", balance=0)

    with pytest.raises(ValueError, match="positive integer"):
        await validator.validate(
            True,
            account=account,
            metadata={"dynamic_amount": "999999999; DROP TABLE accounts"},
            conn=mock_conn,
        )
