from dataclasses import dataclass


@dataclass
class Account:
    id: str
    balance: int

    def debit(self, amount: int):
        if self.balance < amount:
            raise ValueError("Insufficient funds")
        self.balance -= amount

    def credit(self, amount: int):
        self.balance += amount
