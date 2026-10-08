import uuid

from sqlalchemy import func, select

from app.core.pagination import Page, PageParams
from app.models.course import Course
from app.models.department import Department
from app.models.student import Student
from app.models.teacher import Teacher
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def name_taken(self, name: str, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._value_taken(Department.name, name, exclude_id)

    async def code_taken(self, code: str, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._value_taken(Department.code, code, exclude_id)

    async def _value_taken(self, column, value: str, exclude_id: uuid.UUID | None) -> bool:
        stmt = select(func.count()).select_from(Department).where(func.lower(column) == value.lower())
        if exclude_id is not None:
            stmt = stmt.where(Department.id != exclude_id)
        return (await self._session.execute(stmt)).scalar_one() > 0

    async def search(self, params: PageParams) -> Page[Department]:
        stmt = select(Department)
        clause = self.search_clause(params.search, [Department.name, Department.code])
        if clause is not None:
            stmt = stmt.where(clause)
        return await self.paginate(
            stmt,
            params,
            sortable={
                "id": Department.id,
                "name": Department.name,
                "code": Department.code,
                "createdAt": Department.created_at,
            },
            default_sort=[Department.name.asc()],
        )

    async def count_references(self, department_id: uuid.UUID) -> dict[str, int]:
        """Number of teachers, students and courses that reference the department."""
        counts: dict[str, int] = {}
        for label, column in (
            ("teachers", Teacher.department_id),
            ("students", Student.department_id),
            ("courses", Course.department_id),
        ):
            stmt = select(func.count()).select_from(column.class_).where(column == department_id)
            counts[label] = (await self._session.execute(stmt)).scalar_one()
        return counts
