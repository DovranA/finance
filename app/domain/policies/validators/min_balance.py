from domain.policies.base import ConditionValidator


class MinBalanceValidator(ConditionValidator):
    key = "min_balance"

    async def validate(self, value, *, account, **kwargs):
        if account.balance < value:
            raise Exception("Insufficient balance")
