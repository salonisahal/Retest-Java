import uuid

from sqlalchemy import select

from app.models.course import Course
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    model = Course

    async def list_ids_by_teacher(self, teacher_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(Course.id).where(Course.teacher_id == teacher_id)
        return list((await self.session.execute(stmt)).scalars().all())
