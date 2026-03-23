import shared_pb2 as _shared_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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

class Event(_message.Message):
    __slots__ = ("event_code", "post_id", "author_id", "view_percentage", "metadata")
    EVENT_CODE_FIELD_NUMBER: _ClassVar[int]
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    VIEW_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    event_code: _containers.RepeatedScalarFieldContainer[str]
    post_id: str
    author_id: str
    view_percentage: int
    metadata: _struct_pb2.Struct
    def __init__(self, event_code: _Optional[_Iterable[str]] = ..., post_id: _Optional[str] = ..., author_id: _Optional[str] = ..., view_percentage: _Optional[int] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class UserEngagedList(_message.Message):
    __slots__ = ("header", "user_id", "role", "post_list")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    POST_LIST_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    role: str
    post_list: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ..., user_id: _Optional[str] = ..., role: _Optional[str] = ..., post_list: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...
