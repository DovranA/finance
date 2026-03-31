import datetime

from . import shared_pb2 as _shared_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UserCompetitionJoined(_message.Message):
    __slots__ = ("header", "competition_id", "user_id", "joined_at", "with_gift")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    COMPETITION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    JOINED_AT_FIELD_NUMBER: _ClassVar[int]
    WITH_GIFT_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    competition_id: str
    user_id: str
    joined_at: _timestamp_pb2.Timestamp
    with_gift: bool
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        competition_id: _Optional[str] = ...,
        user_id: _Optional[str] = ...,
        joined_at: _Optional[
            _Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]
        ] = ...,
        with_gift: bool = ...,
    ) -> None: ...
