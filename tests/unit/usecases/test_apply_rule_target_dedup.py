from __future__ import annotations

import uuid

from app.domain.entities.rule import Rule
from app.usecases.apply_rule import ApplyRuleUseCase


def _rule(target_users: list[str]) -> Rule:
    return Rule.create(event_code="LIKE", actions={"target_users": target_users})


def test_self_interaction_is_paid_only_once():
    same_user = uuid.uuid4()
    rule = _rule(["user_id", "author_id"])

    targets = ApplyRuleUseCase._resolve_target_users(
        rule,
        {
            "user_id": str(same_user),
            "metadata": {"author_id": str(same_user)},
        },
    )

    assert targets == [("user_id", same_user)]


def test_different_users_are_both_paid():
    actor = uuid.uuid4()
    author = uuid.uuid4()
    rule = _rule(["user_id", "author_id"])

    targets = ApplyRuleUseCase._resolve_target_users(
        rule,
        {
            "user_id": str(actor),
            "metadata": {"author_id": str(author)},
        },
    )

    assert set(targets) == {("user_id", actor), ("author_id", author)}
