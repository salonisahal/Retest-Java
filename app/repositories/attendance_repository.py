import datetime as dt
import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class AttendanceFilters:
    """User-supplied filters plus access-scope restrictions (``restrict_*`` are set by the service)."""

    student_id: uuid.UUID | None = None
    course_id: uuid.UUID | None = None
    status: AttendanceStatus | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    restrict_course_ids: Collection[uuid.UUID] | None = None
    restrict_student_id: uuid.UUID | None = None


class AttendanceRepository(BaseRepository[Attendance]):
    model = Attendance

    async def search(self, params: PageParams, filters: AttendanceFilters) -> Page[Attendance]:
        conditions = []
        if filters.student_id is not None:
            conditions.append(Attendance.student_id == filters.student_id)
        if filters.course_id is not None:
            conditions.append(Attendance.course_id == filters.course_id)
        if filters.status is not None:
            conditions.append(Attendance.status == filters.status)
        if filters.date_from is not None:
            conditions.append(Attendance.date >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(Attendance.date <= filters.date_to)
        if filters.restrict_course_ids is not None:
            conditions.append(Attendance.course_id.in_(list(filters.restrict_course_ids)))
        if filters.restrict_student_id is not None:
            conditions.append(Attendance.student_id == filters.restrict_student_id)

        stmt = select(Attendance)
        if conditions:
            stmt = stmt.where(*conditions)
        sortable = {
            "id": Attendance.id,
            "date": Attendance.date,
            "status": Attendance.status,
            "createdAt": Attendance.created_at,
        }
        return await self.paginate(stmt, params, sortable, default_sort=[Attendance.date.desc(), Attendance.id])

    async def find_duplicate(
        self,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        date: dt.date,
        exclude_id: uuid.UUID | None = None,
    ) -> Attendance | None:
        stmt = select(Attendance).where(
            Attendance.student_id == student_id,
            Attendance.course_id == course_id,
            Attendance.date == date,
        )
        if exclude_id is not None:
            stmt = stmt.where(Attendance.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalars().first()
