from app.domain.policies.base import ConditionValidator


class DailyLimitValidator(ConditionValidator):
    key = "daily_limit"

    async def validate(self, value, *, account, metadata, db, **kwargs):
        count = await db.fetchval(
            """
            SELECT COUNT(*)
            FROM ledger_entries
            WHERE account_id = $1
              AND entry_type = $2
              AND created_at >= CURRENT_DATE
            """,
            account.id,
            metadata["event_code"],
        )

        if count >= value:
            raise Exception("Daily limit exceeded")
