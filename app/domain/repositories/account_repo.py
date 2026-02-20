from abc import ABC, abstractmethod

from app.domain.entries.account import Account


class AccountRepository(ABC):

    @abstractmethod
    async def get(self, account_id: str) -> Account:
        pass

    @abstractmethod
    async def save(self, account: Account):
        pass
