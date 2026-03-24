"""Domain enums for the finance microservice."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    TOKEN = "TOKEN"
    COIN = "COIN"
    DIAMOND = "DIAMOND"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class EntryType(StrEnum):
    ACTOR_REWARD = "actor_reward"
    PUBLISHER_REWARD = "publisher_reward"
    PLATFORM_FEE = "platform_fee"
    TREASURY_CUT = "treasury_cut"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class BatchStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"


class AccountTypes(StrEnum):
    USER = "user"
    TREASURY = "treasury"
    REWARD_POOL = "reward_pool"


class LedgerDirection(IntEnum):
    DIRECTION_DEBIT = -1
    DIRECTION_CREDIT = 1
