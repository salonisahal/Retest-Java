import uuid

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.course import ClassSession
from app.models.enums import ScheduleDay
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository[ClassSession]):
    model = ClassSession

    async def search(
        self,
        params: PageParams,
        course_id: uuid.UUID | None = None,
        teacher_id: uuid.UUID | None = None,
        schedule_day: ScheduleDay | None = None,
    ) -> Page[ClassSession]:
        stmt = select(ClassSession)
        if course_id is not None:
            stmt = stmt.where(ClassSession.course_id == course_id)
        if teacher_id is not None:
            stmt = stmt.where(ClassSession.teacher_id == teacher_id)
        if schedule_day is not None:
            stmt = stmt.where(ClassSession.schedule_day == schedule_day)
        clause = self.search_clause(params.search, [ClassSession.name, ClassSession.room])
        if clause is not None:
            stmt = stmt.where(clause)
        sortable = {
            "id": ClassSession.id,
            "name": ClassSession.name,
            "room": ClassSession.room,
            "scheduleDay": ClassSession.schedule_day,
            "startTime": ClassSession.start_time,
            "createdAt": ClassSession.created_at,
        }
        return await self.paginate(
            stmt, params, sortable, default_sort=[ClassSession.created_at.desc(), ClassSession.id.asc()]
        )
