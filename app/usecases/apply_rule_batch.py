"""Batch wrapper for applying one rule per user event payload."""

from __future__ import annotations

from typing import Any

from app.usecases.apply_rule import ApplyRuleUseCase


class BatchApplyRuleUseCase:
    """Execute ApplyRuleUseCase repeatedly for a batch payload."""

    def __init__(self, apply_rule_uc: ApplyRuleUseCase) -> None:
        self._apply_rule_uc = apply_rule_uc

    async def execute(
        self,
        *,
        event_code: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self._apply_rule_uc.execute_batch(
            event_code=event_code,
            items=items,
        )
