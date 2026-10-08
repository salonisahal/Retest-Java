import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.enums import AssignmentStatus, EnrollmentStatus
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class AssignmentFilters:
    """User-supplied filters plus access-scope restrictions (``restrict_*``, ``published_only``)."""

    course_id: uuid.UUID | None = None
    status: AssignmentStatus | None = None
    search: str | None = None
    restrict_course_ids: Collection[uuid.UUID] | None = None
    published_only: bool = False


class AssignmentRepository(BaseRepository[Assignment]):
    model = Assignment

    async def search(self, params: PageParams, filters: AssignmentFilters) -> Page[Assignment]:
        conditions = []
        if filters.course_id is not None:
            conditions.append(Assignment.course_id == filters.course_id)
        if filters.status is not None:
            conditions.append(Assignment.status == filters.status)
        if filters.restrict_course_ids is not None:
            conditions.append(Assignment.course_id.in_(list(filters.restrict_course_ids)))
        if filters.published_only:
            conditions.append(Assignment.status == AssignmentStatus.PUBLISHED)
        search_clause = self.search_clause(filters.search, [Assignment.title])
        if search_clause is not None:
            conditions.append(search_clause)

        stmt = select(Assignment)
        if conditions:
            stmt = stmt.where(*conditions)
        sortable = {
            "id": Assignment.id,
            "title": Assignment.title,
            "dueDate": Assignment.due_date,
            "maxMarks": Assignment.max_marks,
            "status": Assignment.status,
            "createdAt": Assignment.created_at,
        }
        return await self.paginate(stmt, params, sortable, default_sort=[Assignment.due_date.desc(), Assignment.id])

    async def active_course_ids_for_student(self, student_id: uuid.UUID) -> list[uuid.UUID]:
        """Courses the student is currently (ACTIVE enrollment) enrolled in."""
        stmt = (
            select(Enrollment.course_id)
            .where(Enrollment.student_id == student_id, Enrollment.status == EnrollmentStatus.ACTIVE)
            .distinct()
        )
        return list((await self.session.execute(stmt)).scalars().all())
