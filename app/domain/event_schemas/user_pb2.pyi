from . import shared_pb2 as _shared_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EngagementType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ENGAGEMENT_UNKNOWN: _ClassVar[EngagementType]
    LIKE: _ClassVar[EngagementType]
    BOOKMARK: _ClassVar[EngagementType]
    VIEW: _ClassVar[EngagementType]
    REPOST: _ClassVar[EngagementType]

class ShareType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SHARE_UNKNOWN: _ClassVar[ShareType]
    POST: _ClassVar[ShareType]
    USER: _ClassVar[ShareType]

ENGAGEMENT_UNKNOWN: EngagementType
LIKE: EngagementType
BOOKMARK: EngagementType
VIEW: EngagementType
REPOST: EngagementType
SHARE_UNKNOWN: ShareType
POST: ShareType
USER: ShareType

class EngagedPost(_message.Message):
    __slots__ = ("id", "view_percentage", "liked", "bookmarked", "reposted")
    ID_FIELD_NUMBER: _ClassVar[int]
    VIEW_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    LIKED_FIELD_NUMBER: _ClassVar[int]
    BOOKMARKED_FIELD_NUMBER: _ClassVar[int]
    REPOSTED_FIELD_NUMBER: _ClassVar[int]
    id: str
    view_percentage: int
    liked: bool
    bookmarked: bool
    reposted: bool
    def __init__(
        self,
        id: _Optional[str] = ...,
        view_percentage: _Optional[int] = ...,
        liked: bool = ...,
        bookmarked: bool = ...,
        reposted: bool = ...,
    ) -> None: ...

class UserEngaged(_message.Message):
    __slots__ = ("header", "user_id", "engaged_posts")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ENGAGED_POSTS_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    engaged_posts: _containers.RepeatedCompositeFieldContainer[EngagedPost]
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        engaged_posts: _Optional[_Iterable[_Union[EngagedPost, _Mapping]]] = ...,
    ) -> None: ...

class UserRegistered(_message.Message):
    __slots__ = ("header", "user_id", "tags", "gender", "birth_date", "regions", "role")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    BIRTH_DATE_FIELD_NUMBER: _ClassVar[int]
    REGIONS_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    tags: _containers.RepeatedCompositeFieldContainer[Tags]
    gender: str
    birth_date: str
    regions: _containers.RepeatedScalarFieldContainer[str]
    role: str
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        tags: _Optional[_Iterable[_Union[Tags, _Mapping]]] = ...,
        gender: _Optional[str] = ...,
        birth_date: _Optional[str] = ...,
        regions: _Optional[_Iterable[str]] = ...,
        role: _Optional[str] = ...,
    ) -> None: ...

class Tags(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: int
    def __init__(
        self, key: _Optional[str] = ..., value: _Optional[int] = ...
    ) -> None: ...

class UserDeleted(_message.Message):
    __slots__ = ("header", "user_id", "role")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    role: str
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        role: _Optional[str] = ...,
    ) -> None: ...

class UserInteracted(_message.Message):
    __slots__ = ("header", "user_id", "interactedPosts", "userShared", "userInvited")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    INTERACTEDPOSTS_FIELD_NUMBER: _ClassVar[int]
    USERSHARED_FIELD_NUMBER: _ClassVar[int]
    USERINVITED_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    interactedPosts: _containers.RepeatedCompositeFieldContainer[InteractedPost]
    userShared: UserShared
    userInvited: UserInvited
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        interactedPosts: _Optional[_Iterable[_Union[InteractedPost, _Mapping]]] = ...,
        userShared: _Optional[_Union[UserShared, _Mapping]] = ...,
        userInvited: _Optional[_Union[UserInvited, _Mapping]] = ...,
    ) -> None: ...

class InteractedPost(_message.Message):
    __slots__ = ("post_id", "author_id", "event_type", "view_percentage")
    POST_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    VIEW_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    post_id: str
    author_id: str
    event_type: EngagementType
    view_percentage: int
    def __init__(
        self,
        post_id: _Optional[str] = ...,
        author_id: _Optional[str] = ...,
        event_type: _Optional[_Union[EngagementType, str]] = ...,
        view_percentage: _Optional[int] = ...,
    ) -> None: ...

class UserShared(_message.Message):
    __slots__ = ("shared_id", "share_type", "author_id", "shared_to_user_id")
    SHARED_ID_FIELD_NUMBER: _ClassVar[int]
    SHARE_TYPE_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    SHARED_TO_USER_ID_FIELD_NUMBER: _ClassVar[int]
    shared_id: str
    share_type: ShareType
    author_id: str
    shared_to_user_id: str
    def __init__(
        self,
        shared_id: _Optional[str] = ...,
        share_type: _Optional[_Union[ShareType, str]] = ...,
        author_id: _Optional[str] = ...,
        shared_to_user_id: _Optional[str] = ...,
    ) -> None: ...

class UserInvited(_message.Message):
    __slots__ = ("invited_user_id",)
    INVITED_USER_ID_FIELD_NUMBER: _ClassVar[int]
    invited_user_id: str
    def __init__(self, invited_user_id: _Optional[str] = ...) -> None: ...

class UserReported(_message.Message):
    __slots__ = ("header", "user_id", "is_blocked")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    IS_BLOCKED_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    is_blocked: bool
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        is_blocked: bool = ...,
    ) -> None: ...

class UserFollowed(_message.Message):
    __slots__ = ("header", "user_id", "follower_id")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    FOLLOWER_ID_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    user_id: str
    follower_id: str
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        user_id: _Optional[str] = ...,
        follower_id: _Optional[str] = ...,
    ) -> None: ...

class UserUpdated(_message.Message):
    __slots__ = ("header", "role", "username", "full_name", "user_id")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    FULL_NAME_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    header: _shared_pb2.EventHeader
    role: str
    username: str
    full_name: str
    user_id: str
    def __init__(
        self,
        header: _Optional[_Union[_shared_pb2.EventHeader, _Mapping]] = ...,
        role: _Optional[str] = ...,
        username: _Optional[str] = ...,
        full_name: _Optional[str] = ...,
        user_id: _Optional[str] = ...,
    ) -> None: ...
