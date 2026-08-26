from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from asyncpg import Connection

from app.domain.policies.base import ConditionValidator


@dataclass(frozen=True)
class ViewPercentageCase:
    full_at: int = 100
    zero_below: int = 10
    half_below: int = 40
    half_multiplier: float = 0.5
    default_multiplier: float = 0.0

    @classmethod
    def from_value(cls, value: Any) -> ViewPercentageCase:
        if not isinstance(value, dict):
            raise ValueError("view_percentage case must be a mapping")

        full_at = int(value.get("full_at", 100))
        zero_below = int(value.get("zero_below", 10))
        half_below = int(value.get("half_below", 40))
        half_multiplier = float(value.get("half_multiplier", 0.5))
        default_multiplier = float(value.get("default_multiplier", 0.0))

        if full_at < 0 or full_at > 100:
            raise ValueError("view_percentage.full_at must be between 0 and 100")
        if zero_below < 0 or zero_below > 100:
            raise ValueError("view_percentage.zero_below must be between 0 and 100")
        if half_below < 0 or half_below > 100:
            raise ValueError("view_percentage.half_below must be between 0 and 100")
        if zero_below > half_below:
            raise ValueError("view_percentage.zero_below must be <= half_below")

        return cls(
            full_at=full_at,
            zero_below=zero_below,
            half_below=half_below,
            half_multiplier=half_multiplier,
            default_multiplier=default_multiplier,
        )

    def resolve(self, view_percentage: int) -> tuple[str, float]:
        if view_percentage >= self.full_at:
            return "full", 1.0

        if view_percentage < self.zero_below:
            return "zero", 0.0

        if view_percentage < self.half_below:
            return "half", self.half_multiplier

        return "default", self.default_multiplier


class ViewPercentageValidator(ConditionValidator):
    key = "view_percentage"

    async def validate(
        self,
        value: Any,
        *,
        account: Any,
        metadata: dict[str, Any],
        conn: Connection,
    ) -> None:
        if value is None:
            return

        raw_percentage = metadata.get("view_percentage")
        if raw_percentage is None:
            raise ValueError("Missing metadata: view_percentage")

        try:
            view_percentage = int(raw_percentage)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata.view_percentage must be an integer") from exc

        if isinstance(value, dict):
            case = ViewPercentageCase.from_value(value)
            band, multiplier = case.resolve(view_percentage)
            metadata["view_percentage_band"] = band
            metadata["view_percentage_multiplier"] = multiplier
            return

        try:
            threshold = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("view_percentage must be an integer or mapping") from exc

        if threshold < 0 or threshold > 100:
            raise ValueError("view_percentage must be between 0 and 100")

        if view_percentage < threshold:
            raise ValueError(
                f"view_percentage {view_percentage} is below required minimum {threshold}"
            )
