from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import asyncpg


UUID_NAMESPACE = uuid.UUID("f7cf76d8-434e-44c4-b9f9-e918f0f33203")


@dataclass
class Counters:
    source_accounts: int = 0
    inserted_or_updated_accounts: int = 0
    source_transactions: int = 0
    inserted_transactions: int = 0
    inserted_ledger_entries: int = 0
    skipped_transactions_invalid_user: int = 0
    skipped_transactions_zero_amount: int = 0
    source_prices: int = 0
    upserted_rules: int = 0


def stable_uuid(kind: str, *parts: Any) -> uuid.UUID:
    payload = "|".join([kind, *[str(p) for p in parts]])
    return uuid.uuid5(UUID_NAMESPACE, payload)


def parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        return None


def normalize_event_code(raw: str) -> str:
    code = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()
    if len(code) <= 120:
        return code
    digest = hashlib.sha1(code.encode("utf-8")).hexdigest()[:8]
    return f"{code[:111]}_{digest}"


def make_idempotency_key(old_tx_id: int, reference_id: str | None) -> str:
    ref = reference_id or ""
    digest = hashlib.sha1(ref.encode("utf-8")).hexdigest()[:16]
    key = f"legacy_tx_{old_tx_id}_{digest}"
    return key[:256]


async def migrate(args: argparse.Namespace) -> None:
    source = await asyncpg.connect(args.source_dsn)
    target = await asyncpg.connect(args.target_dsn)
    c = Counters()

    try:
        if args.only_with_transactions:
            source_accounts = await source.fetch(
                """
                SELECT a.id, a.user_id, a.token, a.coin, a.created_at, a.updated_at
                FROM public.accounts a
                JOIN (
                    SELECT DISTINCT account_id
                    FROM public.transactions
                ) tx ON tx.account_id = a.id
                ORDER BY a.id
                LIMIT $1
                """,
                args.account_limit,
            )
        else:
            source_accounts = await source.fetch(
                """
                SELECT id, user_id, token, coin, created_at, updated_at
                FROM public.accounts
                ORDER BY id
                LIMIT $1
                """,
                args.account_limit,
            )
        c.source_accounts = len(source_accounts)

        old_account_ids = [r["id"] for r in source_accounts]
        user_map: dict[int, uuid.UUID] = {}

        async with target.transaction():
            for row in source_accounts:
                old_account_id = row["id"]
                user_uuid = parse_uuid(row["user_id"])
                if user_uuid is None:
                    continue

                user_map[old_account_id] = user_uuid
                created_at = row["created_at"]
                updated_at = row["updated_at"]

                for balance_type, currency in (("token", "TOKEN"), ("coin", "COIN")):
                    amount = row[balance_type]
                    new_account_id = stable_uuid("account", old_account_id, currency)
                    await target.fetchval(
                        """
                        INSERT INTO public.accounts (
                            id,
                            user_id,
                            owner_type,
                            currency,
                            balance,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES ($1, $2, 'user', $3, $4, TRUE, $5, $6)
                        ON CONFLICT (owner_type, currency, user_id)
                        DO UPDATE SET
                            balance = EXCLUDED.balance,
                            is_active = TRUE,
                            updated_at = EXCLUDED.updated_at
                        RETURNING id
                        """,
                        new_account_id,
                        user_uuid,
                        currency,
                        int(amount),
                        created_at,
                        updated_at,
                    )
                    c.inserted_or_updated_accounts += 1

            source_transactions = await source.fetch(
                """
                SELECT
                    t.id,
                    t.account_id,
                    t.transaction_type,
                    t.amount,
                    t.post_id,
                    t.target_type,
                    t.created_at,
                    t.updated_at,
                    t.price_id,
                    t.is_synced,
                    t.balance_type,
                    t.quantity,
                    t.expire_date,
                    t.reference_id,
                    p.code AS price_code
                FROM public.transactions t
                LEFT JOIN public.prices p ON p.id = t.price_id
                WHERE t.account_id = ANY($1::int[])
                ORDER BY t.id
                """,
                old_account_ids,
            )
            c.source_transactions = len(source_transactions)

            for tx in source_transactions:
                old_account_id = tx["account_id"]
                user_uuid = user_map.get(old_account_id)
                if user_uuid is None:
                    c.skipped_transactions_invalid_user += 1
                    continue

                balance_type = (tx["balance_type"] or "TOKEN").upper()
                currency = "COIN" if balance_type == "COIN" else "TOKEN"
                new_account_id = stable_uuid("account", old_account_id, currency)

                old_tx_id = tx["id"]
                new_tx_id = stable_uuid("transaction", old_tx_id)
                amount = int(tx["amount"])
                if amount == 0:
                    c.skipped_transactions_zero_amount += 1
                    continue

                idempotency_key = make_idempotency_key(old_tx_id, tx["reference_id"])
                direction = (
                    1 if (tx["transaction_type"] or "").upper() == "INCREASE" else -1
                )

                metadata = {
                    "legacy": {
                        "old_transaction_id": old_tx_id,
                        "old_account_id": old_account_id,
                        "price_id": tx["price_id"],
                        "price_code": tx["price_code"],
                        "quantity": tx["quantity"],
                        "target_type": tx["target_type"],
                        "balance_type": balance_type,
                        "transaction_type": tx["transaction_type"],
                        "post_id": tx["post_id"],
                        "is_synced": tx["is_synced"],
                    }
                }

                tx_insert = await target.execute(
                    """
                    INSERT INTO public.transactions (
                        id,
                        idempotency_key,
                        status,
                        reference_type,
                        reference_id,
                        metadata,
                        created_at,
                        expires_at
                    )
                    VALUES ($1, $2, 'completed', $3, $4, $5::jsonb, $6, $7)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    new_tx_id,
                    idempotency_key,
                    tx["transaction_type"] or "legacy",
                    (tx["reference_id"] or "")[:256],
                    json.dumps(metadata),
                    tx["created_at"],
                    tx["expire_date"],
                )
                if tx_insert.endswith(" 1"):
                    c.inserted_transactions += 1

                ledger_insert = await target.execute(
                    """
                    INSERT INTO public.ledger_entries (
                        id,
                        account_id,
                        transaction_id,
                        amount,
                        direction,
                        created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    stable_uuid("ledger", old_tx_id),
                    new_account_id,
                    new_tx_id,
                    abs(amount),
                    direction,
                    tx["created_at"],
                )
                if ledger_insert.endswith(" 1"):
                    c.inserted_ledger_entries += 1

            source_prices = await source.fetch(
                """
                SELECT
                    id,
                    code,
                    price_type,
                    target_type,
                    price_amount,
                    created_at,
                    updated_at,
                    name_tm,
                    name_ru,
                    name_en,
                    balance_type,
                    expire_days,
                    filter_type,
                    cost
                FROM public.prices
                ORDER BY id
                """
            )
            c.source_prices = len(source_prices)

            for price in source_prices:
                price_id = price["id"]
                event_code = normalize_event_code(
                    f"legacy_price_{price_id}_{price['code']}_{price['price_type']}_{price['target_type']}_{price['balance_type']}"
                )

                direction = (
                    1 if (price["price_type"] or "").upper() == "INCREASE" else -1
                )
                created_at = price["created_at"]
                expired_at = None
                if price["expire_days"] is not None:
                    expired_at = created_at + timedelta(days=int(price["expire_days"]))

                conditions = {
                    "source": "legacy_prices",
                    "legacy_price_id": price_id,
                    "target_type": price["target_type"],
                }
                if price["filter_type"]:
                    conditions["filter_type"] = price["filter_type"]

                actions = {
                    "direction": direction,
                    "currency": (price["balance_type"] or "TOKEN").upper(),
                    "reward": int(price["price_amount"]),
                    "quantity": int(price["quantity"]) if "quantity" in price else 1,
                    "cost": float(price["cost"] or 0),
                }

                description = f"Legacy price {price['code']} ({price['price_type']}/{price['target_type']}/{price['balance_type']})"
                description_i18n = {
                    "en": price["name_en"] or description,
                    "ru": price["name_ru"] or "",
                    "tm": price["name_tm"] or "",
                }

                await target.execute(
                    """
                    INSERT INTO public.rules (
                        id,
                        event_code,
                        description,
                        description_i18n,
                        conditions,
                        actions,
                        priority,
                        is_active,
                        expired_at,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4::jsonb,
                        $5::jsonb,
                        $6::jsonb,
                        1,
                        TRUE,
                        $7,
                        $8,
                        $9
                    )
                    ON CONFLICT (event_code)
                    DO UPDATE SET
                        description = EXCLUDED.description,
                        description_i18n = EXCLUDED.description_i18n,
                        conditions = EXCLUDED.conditions,
                        actions = EXCLUDED.actions,
                        expired_at = EXCLUDED.expired_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    stable_uuid("rule", price_id),
                    event_code,
                    description,
                    json.dumps(description_i18n),
                    json.dumps(conditions),
                    json.dumps(actions),
                    expired_at,
                    created_at,
                    price["updated_at"],
                )
                c.upserted_rules += 1

        print("Migration completed.")
        print(f"source_accounts={c.source_accounts}")
        print(f"inserted_or_updated_accounts={c.inserted_or_updated_accounts}")
        print(f"source_transactions={c.source_transactions}")
        print(f"inserted_transactions={c.inserted_transactions}")
        print(f"inserted_ledger_entries={c.inserted_ledger_entries}")
        print(
            f"skipped_transactions_invalid_user={c.skipped_transactions_invalid_user}"
        )
        print(f"skipped_transactions_zero_amount={c.skipped_transactions_zero_amount}")
        print(f"source_prices={c.source_prices}")
        print(f"upserted_rules={c.upserted_rules}")
    finally:
        await source.close()
        await target.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate old economy_db data to new finance schema."
    )
    parser.add_argument(
        "--source-dsn",
        default="postgresql://postgres:12345@127.0.0.1:5433/economy_db",
        help="Source old DB DSN",
    )
    parser.add_argument(
        "--target-dsn",
        default="postgresql://finance_user:finance_secret@127.0.0.1:5432/finance_db",
        help="Target new DB DSN",
    )
    parser.add_argument(
        "--account-limit",
        type=int,
        default=100,
        help="Number of source accounts to migrate",
    )
    parser.add_argument(
        "--only-with-transactions",
        action="store_true",
        default=True,
        help="Select only accounts that have at least one transaction",
    )
    parser.add_argument(
        "--include-empty-accounts",
        action="store_true",
        help="Override to allow selecting accounts without transactions",
    )
    return parser


if __name__ == "__main__":
    import asyncio

    args = build_parser().parse_args()
    if args.include_empty_accounts:
        args.only_with_transactions = False
    asyncio.run(migrate(args))
