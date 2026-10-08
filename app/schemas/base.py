"""Shared Pydantic base models (camelCase wire format) and the response envelopes."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base for every request/response DTO: camelCase aliases, ORM-attribute reading, snake_case input accepted."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class PaginationInfo(CamelModel):
    page: int
    size: int
    total_elements: int
    total_pages: int


class ApiResponse(CamelModel, Generic[T]):
    """Success envelope: {success, message, data}."""

    success: bool = True
    message: str = "Operation successful"
    data: T | None = None


class PagedApiResponse(CamelModel, Generic[T]):
    """Success envelope for list endpoints: {success, message, data, pagination}."""

    success: bool = True
    message: str = "Operation successful"
    data: list[T]
    pagination: PaginationInfo


class ErrorResponse(CamelModel):
    """Documented error envelope (used for OpenAPI only; handlers build the dict directly)."""

    success: bool = False
    message: str
    error_code: str
    timestamp: str
    path: str
    errors: dict[str, list[str]] | None = None
