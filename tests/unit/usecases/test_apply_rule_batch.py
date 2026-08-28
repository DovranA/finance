from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.usecases.apply_rule as apply_rule_module
from app.domain.entities.account import Account
from app.domain.entities.rule import Rule
from app.domain.exceptions import DuplicateOperation
from app.usecases.apply_rule import ApplyRuleUseCase


class _FakeConditionEngine:
    """Fails only the author_id target, like a real one_time_only duplicate."""

    async def validate(self, conditions, *, account, metadata, conn):
        if metadata.get("target_key") == "author_id":
            raise DuplicateOperation("one_time:fake")


def _make_conn() -> MagicMock:
    conn = MagicMock()
    savepoint = AsyncMock()
    conn.transaction = MagicMock(return_value=savepoint)
    return conn


@pytest.mark.asyncio
async def test_author_side_duplicate_does_not_wipe_actor_reward(monkeypatch):
    actor_id = uuid.uuid4()
    author_id = uuid.uuid4()
    post_id = uuid.uuid4()

    conn = _make_conn()

    @asynccontextmanager
    async def _fake_transaction(pool):
        yield conn

    monkeypatch.setattr(apply_rule_module, "transaction", _fake_transaction)

    rule = Rule.create(
        event_code="LIKE",
        conditions={"one_time_only": True},
        actions={
            "direction": 1,
            "currency": "TOKEN",
            "target_users": ["user_id", "author_id"],
            "target_amounts": {"user_id": 1, "author_id": 2},
        },
    )

    actor_account = Account.create(
        user_id=actor_id, currency="TOKEN", owner_type="user", balance=0
    )
    author_account = Account.create(
        user_id=author_id, currency="TOKEN", owner_type="user", balance=0
    )
    treasury_account = Account.create(
        user_id=None, currency="TOKEN", owner_type="treasury", balance=1_000_000
    )
    accounts_by_owner = {actor_id: actor_account, author_id: author_account}

    rule_repo = MagicMock()
    rule_repo.get_active_by_event_code = AsyncMock(return_value=rule)

    account_repo = MagicMock()
    account_repo.get_by_account_type = AsyncMock(return_value=treasury_account)
    account_repo.get_by_owner_id_for_update = AsyncMock(
        side_effect=lambda user_id, conn, currency=None: accounts_by_owner[user_id]
    )
    account_repo.update_balance = AsyncMock()

    transaction_repo = MagicMock()
    transaction_repo.get_by_key = AsyncMock(return_value=None)
    transaction_repo.save_many = AsyncMock(
        side_effect=lambda txs, conn: [tx.id for tx in txs]
    )

    ledger_repo = MagicMock()
    ledger_repo.insert_many = AsyncMock()

    use_case = ApplyRuleUseCase(
        pool=MagicMock(),
        rule_repo=rule_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        ledger_repo=ledger_repo,
        user_gateway=MagicMock(),
        condition_engine=_FakeConditionEngine(),
        cache=None,
    )

    result = await use_case.execute_batch(
        event_code="LIKE",
        items=[
            {
                "user_id": str(actor_id),
                "event_id": str(uuid.uuid4()),
                "role": "simple",
                "metadata": {"post_id": str(post_id), "author_id": str(author_id)},
            }
        ],
    )

    assert result["applied"] == 1
    assert result["results"][0]["applied"] is True
    assert "one_time:fake" in (result["results"][0]["error"] or "")

    inserted_entries = ledger_repo.insert_many.await_args.args[0]
    assert any(entry.account_id == actor_account.id for entry in inserted_entries)
    assert not any(entry.account_id == author_account.id for entry in inserted_entries)
