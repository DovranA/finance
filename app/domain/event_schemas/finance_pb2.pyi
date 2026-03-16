from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetBalanceRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class GetBalanceResponse(_message.Message):
    __slots__ = ("user_id", "account_id", "balance", "currency", "cached")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    BALANCE_FIELD_NUMBER: _ClassVar[int]
    CURRENCY_FIELD_NUMBER: _ClassVar[int]
    CACHED_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    account_id: str
    balance: int
    currency: str
    cached: bool
    def __init__(self, user_id: _Optional[str] = ..., account_id: _Optional[str] = ..., balance: _Optional[int] = ..., currency: _Optional[str] = ..., cached: bool = ...) -> None: ...
