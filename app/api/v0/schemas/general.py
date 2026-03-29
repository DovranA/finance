from typing import Generic, TypeVar, List
from pydantic import BaseModel

# Define a TypeVar to represent the generic data type
T = TypeVar("T")


class PageInfo(BaseModel):
    has_next_page: bool
    has_previous_page: bool
    total_pages: int
    page: int
    limit: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: T
    page_info: PageInfo
