from abc import ABC, abstractmethod


class ConditionValidator(ABC):
    key: str  # имя ключа в JSON

    @abstractmethod
    async def validate(self, value, *, account, metadata, db, redis) -> None: ...
