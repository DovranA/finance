from __future__ import annotations

from app.domain.policies.base import ConditionValidator


class ValidatorRegistry:
    """Registry for condition validators, keyed by their JSON key name."""

    def __init__(self) -> None:
        self._validators: dict[str, ConditionValidator] = {}

    def register(self, validator: ConditionValidator) -> None:
        self._validators[validator.key] = validator

    def get(self, key: str) -> ConditionValidator | None:
        return self._validators.get(key)


registry = ValidatorRegistry()
