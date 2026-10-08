"""Offset pagination primitives (zero-based pages) and envelope builders."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query

from app.schemas.base import ApiResponse, PagedApiResponse, PaginationInfo

T = TypeVar("T")
R = TypeVar("R")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageParams:
    """Parsed list-query parameters: ``page`` (0-based), ``size``, ``search`` and raw ``sort`` (``field,dir``)."""

    page: int = 0
    size: int = DEFAULT_PAGE_SIZE
    search: str | None = None
    sort: str | None = None

    @property
    def offset(self) -> int:
        return self.page * self.size


def get_page_params(
    page: Annotated[int, Query(ge=0, description="Zero-based page index")] = 0,
    size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE, description="Page size")] = DEFAULT_PAGE_SIZE,
    search: Annotated[str | None, Query(description="Free-text search on text fields")] = None,
    sort: Annotated[str | None, Query(description="Sort as 'field,asc|desc'")] = None,
) -> PageParams:
    return PageParams(page=page, size=size, search=search.strip() if search and search.strip() else None, sort=sort)


PageParamsDep = Annotated[PageParams, Depends(get_page_params)]


@dataclass(frozen=True)
class Page(Generic[T]):
    """A page of results produced by a repository/service."""

    items: list[T]
    total: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.size) if self.size else 0

    def map(self, mapper: Callable[[T], R]) -> "Page[R]":
        return Page(items=[mapper(item) for item in self.items], total=self.total, page=self.page, size=self.size)


def success(data: T | None = None, message: str = "Operation successful") -> ApiResponse[T]:
    return ApiResponse(success=True, message=message, data=data)


def paged_success(page: Page[T], message: str = "Operation successful") -> PagedApiResponse[T]:
    return PagedApiResponse(
        success=True,
        message=message,
        data=page.items,
        pagination=PaginationInfo(
            page=page.page, size=page.size, total_elements=page.total, total_pages=page.total_pages
        ),
    )
