"""Generic async repository: CRUD primitives, whitelist-based sorting, search and offset pagination."""

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.exceptions import BadRequestError
from app.core.pagination import Page, PageParams
from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)

SortableFields = Mapping[str, InstrumentedAttribute[Any]]
_SORT_DIRECTIONS = {"asc", "desc"}


class BaseRepository(Generic[ModelT]):
    """Data-access primitives for one ORM model. Never commits; transaction control belongs to services."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self._session.get(self.model, entity_id)

    async def get_by(self, **filters: Any) -> ModelT | None:
        stmt = select(self.model).filter_by(**filters).limit(1)
        return (await self._session.execute(stmt)).scalars().first()

    async def exists_by(self, **filters: Any) -> bool:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return (await self._session.execute(stmt)).scalar_one() > 0

    async def add(self, entity: ModelT) -> ModelT:
        """Stage the entity and flush so constraint violations surface here (IntegrityError)."""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def flush(self) -> None:
        await self._session.flush()

    async def delete(self, entity: ModelT) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def count(self, stmt: Select[Any]) -> int:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        return (await self._session.execute(count_stmt)).scalar_one()

    async def paginate(
        self,
        stmt: Select[Any],
        params: PageParams,
        sortable: SortableFields,
        default_sort: Sequence[Any] = (),
    ) -> Page[ModelT]:
        """Apply whitelisted sorting + offset/limit to a (filtered) ``select(Model)`` statement.

        Raises BadRequestError (400) for an unknown sort field or direction.
        """
        total = await self.count(stmt)
        ordered = stmt.order_by(*self._order_by(params.sort, sortable, default_sort))
        rows = (await self._session.execute(ordered.offset(params.offset).limit(params.size))).scalars().all()
        return Page(items=list(rows), total=total, page=params.page, size=params.size)

    @staticmethod
    def _order_by(sort: str | None, sortable: SortableFields, default_sort: Sequence[Any]) -> list[Any]:
        if not sort:
            return list(default_sort)
        field, _, direction = sort.partition(",")
        field, direction = field.strip(), (direction.strip().lower() or "asc")
        if field not in sortable:
            raise BadRequestError(f"Unknown sort field '{field}'. Allowed: {', '.join(sorted(sortable))}")
        if direction not in _SORT_DIRECTIONS:
            raise BadRequestError("Sort direction must be 'asc' or 'desc'")
        column = sortable[field]
        return [column.desc() if direction == "desc" else column.asc()]

    @staticmethod
    def search_clause(search: str | None, columns: Sequence[Any]) -> Any | None:
        """OR-ed, case-insensitive substring match across the given columns (None when no search term)."""
        if not search:
            return None
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        return or_(*(cast(column, String).ilike(pattern, escape="\\") for column in columns))
