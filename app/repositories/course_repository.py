import uuid

from sqlalchemy import select

from app.core.pagination import Page, PageParams
from app.models.course import Course
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    model = Course

    async def list_ids_by_teacher(self, teacher_id: uuid.UUID) -> list[uuid.UUID]:
        stmt = select(Course.id).where(Course.teacher_id == teacher_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_code(self, course_code: str) -> Course | None:
        return await self.get_by(course_code=course_code)

    async def search(
        self,
        params: PageParams,
        department_id: uuid.UUID | None = None,
        teacher_id: uuid.UUID | None = None,
        semester: int | None = None,
    ) -> Page[Course]:
        stmt = select(Course)
        if department_id is not None:
            stmt = stmt.where(Course.department_id == department_id)
        if teacher_id is not None:
            stmt = stmt.where(Course.teacher_id == teacher_id)
        if semester is not None:
            stmt = stmt.where(Course.semester == semester)
        clause = self.search_clause(params.search, [Course.course_code, Course.course_name])
        if clause is not None:
            stmt = stmt.where(clause)
        sortable = {
            "id": Course.id,
            "courseCode": Course.course_code,
            "courseName": Course.course_name,
            "credits": Course.credits,
            "semester": Course.semester,
            "createdAt": Course.created_at,
        }
        return await self.paginate(stmt, params, sortable, default_sort=[Course.course_code.asc(), Course.id.asc()])
