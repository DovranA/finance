"""Domain enums for the finance microservice."""

from __future__ import annotations

from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"


class EntryType(StrEnum):
    ACTOR_REWARD = "actor_reward"
    PUBLISHER_REWARD = "publisher_reward"
    PLATFORM_FEE = "platform_fee"
    TREASURY_CUT = "treasury_cut"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class BatchStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"


class TreasuryAccountType(StrEnum):
    PLATFORM_FEE = "platform_fee"
    TREASURY = "treasury"


class LedgerEntryType(str, StrEnum):
    CREDIT = "credit"
    DEBIT = "debit"
