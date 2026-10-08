import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.grade import Grade
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class GradeFilters:
    """User-supplied filters plus access-scope restrictions (``restrict_*`` are set by the service)."""

    student_id: uuid.UUID | None = None
    course_id: uuid.UUID | None = None
    assignment_id: uuid.UUID | None = None
    restrict_course_ids: Collection[uuid.UUID] | None = None
    restrict_student_id: uuid.UUID | None = None


class GradeRepository(BaseRepository[Grade]):
    model = Grade

    async def search(self, params: PageParams, filters: GradeFilters) -> Page[Grade]:
        conditions = []
        if filters.student_id is not None:
            conditions.append(Grade.student_id == filters.student_id)
        if filters.course_id is not None:
            conditions.append(Grade.course_id == filters.course_id)
        if filters.assignment_id is not None:
            conditions.append(Grade.assignment_id == filters.assignment_id)
        if filters.restrict_course_ids is not None:
            conditions.append(Grade.course_id.in_(list(filters.restrict_course_ids)))
        if filters.restrict_student_id is not None:
            conditions.append(Grade.student_id == filters.restrict_student_id)

        stmt = select(Grade)
        if conditions:
            stmt = stmt.where(*conditions)
        sortable = {
            "id": Grade.id,
            "marks": Grade.marks,
            "maxMarks": Grade.max_marks,
            "grade": Grade.grade,
            "createdAt": Grade.created_at,
        }
        return await self.paginate(stmt, params, sortable, default_sort=[Grade.created_at.desc(), Grade.id])
