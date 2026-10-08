import uuid
from collections.abc import Collection

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.repositories.base import BaseRepository


class EnrollmentRepository(BaseRepository[Enrollment]):
    model = Enrollment

    async def get_by_unique_key(self, student_id: uuid.UUID, course_id: uuid.UUID, semester: int) -> Enrollment | None:
        return await self.get_by(student_id=student_id, course_id=course_id, semester=semester)

    async def search(
        self,
        params: PageParams,
        student_id: uuid.UUID | None = None,
        course_id: uuid.UUID | None = None,
        semester: int | None = None,
        status: EnrollmentStatus | None = None,
        scope_student_id: uuid.UUID | None = None,
        scope_course_ids: Collection[uuid.UUID] | None = None,
    ) -> Page[Enrollment]:
        """Filtered page. ``scope_*`` restrict visibility by caller role (None = unrestricted)."""
        stmt = select(Enrollment)
        if scope_student_id is not None:
            stmt = stmt.where(Enrollment.student_id == scope_student_id)
        if scope_course_ids is not None:
            stmt = stmt.where(Enrollment.course_id.in_(list(scope_course_ids)))
        if student_id is not None:
            stmt = stmt.where(Enrollment.student_id == student_id)
        if course_id is not None:
            stmt = stmt.where(Enrollment.course_id == course_id)
        if semester is not None:
            stmt = stmt.where(Enrollment.semester == semester)
        if status is not None:
            stmt = stmt.where(Enrollment.status == status)
        sortable = {
            "id": Enrollment.id,
            "semester": Enrollment.semester,
            "status": Enrollment.status,
            "createdAt": Enrollment.created_at,
        }
        return await self.paginate(
            stmt, params, sortable, default_sort=[Enrollment.created_at.desc(), Enrollment.id.asc()]
        )
