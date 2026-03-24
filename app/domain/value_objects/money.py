"""Money value object — wraps BIGINT amount + currency."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.enums import Currency


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable monetary value.

    Amount is stored in the smallest currency unit (e.g. cents for USD).
    All arithmetic is integer-only — no floats ever touch financial values.
    """

    amount: int
    currency: Currency = Currency.TOKEN

    def __post_init__(self) -> None:
        if not isinstance(self.amount, int):
            raise TypeError(f"Money amount must be int, got {type(self.amount)}")

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __neg__(self) -> Money:
        return Money(amount=-self.amount, currency=self.currency)

    def __gt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def __lt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_zero(self) -> bool:
        return self.amount == 0

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot operate on different currencies: "
                f"{self.currency} vs {other.currency}"
            )

    @classmethod
    def zero(cls, currency: Currency = Currency.USD) -> Money:
        return cls(amount=0, currency=currency)
