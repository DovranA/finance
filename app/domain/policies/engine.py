class ConditionEngine:

    def __init__(self, registry):
        self.registry = registry

    async def validate(self, conditions: dict, *, account, metadata, db, redis):
        if not conditions:
            return

        for key, value in conditions.items():
            validator = self.registry.get(key)

            if not validator:
                raise ValueError(f"Unknown condition: {key}")

            await validator.validate(
                value, account=account, metadata=metadata, db=db, redis=redis
            )
