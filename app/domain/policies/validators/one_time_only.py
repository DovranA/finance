from app.domain.policies.base import ConditionValidator


class OneTimeValidator(ConditionValidator):
    key = "one_time_only"

    async def validate(self, value, *, account, metadata, db, **kwargs):
        if not value:
            return

        exists = await db.fetchval(
            """
            SELECT 1
            FROM ledger_entries
            WHERE account_id = $1
              AND reference_id = $2
            LIMIT 1
            """,
            account.id,
            metadata["event_id"],
        )

        if exists:
            raise Exception("Event already used")
