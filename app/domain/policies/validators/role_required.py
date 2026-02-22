from app.domain.policies.base import ConditionValidator


class RoleRequiredValidator(ConditionValidator):
    key = "role_required"

    async def validate(self, value, *, account, **kwargs):
        if account.role not in value:
            raise Exception("Role not allowed")
