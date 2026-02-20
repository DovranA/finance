from dataclasses import dataclass


@dataclass
class LedgerEntry:
    account_id: str
    amount: int
    reference_id: str
