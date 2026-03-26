"""Domain enums for the finance microservice."""

from __future__ import annotations

from enum import Enum


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    RUB = "RUB"
    TOKEN = "TOKEN"
    COIN = "COIN"
    DIAMOND = "DIAMOND"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class EntryType(str, Enum):
    ACTOR_REWARD = "actor_reward"
    PUBLISHER_REWARD = "publisher_reward"
    PLATFORM_FEE = "platform_fee"
    TREASURY_CUT = "treasury_cut"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class BatchStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"


class AccountTypes(str, Enum):
    USER = "user"
    TREASURY = "treasury"
    REWARD_POOL = "reward_pool"


class LedgerDirection(int, Enum):
    DIRECTION_DEBIT = -1
    DIRECTION_CREDIT = 1
