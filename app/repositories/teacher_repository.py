import uuid

from sqlalchemy import func, select

from app.core.pagination import Page, PageParams
from app.models.assignment import Assignment
from app.models.course import ClassSession, Course
from app.models.teacher import Teacher
from app.models.user import User
from app.repositories.base import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    model = Teacher

    async def get_by_user_id(self, user_id: uuid.UUID) -> Teacher | None:
        return await self.get_by(user_id=user_id)

    async def get_fresh(self, teacher_id: uuid.UUID) -> Teacher | None:
        """Load the teacher (and its eagerly-loaded user) from the DB, overwriting any stale identity-map state."""
        stmt = select(Teacher).where(Teacher.id == teacher_id).execution_options(populate_existing=True)
        return (await self._session.execute(stmt)).scalars().first()

    async def employee_id_taken(self, employee_id: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(func.count()).select_from(Teacher).where(Teacher.employee_id == employee_id)
        if exclude_id is not None:
            stmt = stmt.where(Teacher.id != exclude_id)
        return (await self._session.execute(stmt)).scalar_one() > 0

    async def search(self, params: PageParams, department_id: uuid.UUID | None = None) -> Page[Teacher]:
        stmt = select(Teacher).join(User, Teacher.user_id == User.id)
        if department_id is not None:
            stmt = stmt.where(Teacher.department_id == department_id)
        clause = self.search_clause(
            params.search,
            [User.first_name, User.last_name, User.email, Teacher.employee_id, Teacher.specialization],
        )
        if clause is not None:
            stmt = stmt.where(clause)
        return await self.paginate(
            stmt,
            params,
            sortable={
                "id": Teacher.id,
                "employeeId": Teacher.employee_id,
                "specialization": Teacher.specialization,
                "status": Teacher.status,
                "createdAt": Teacher.created_at,
            },
            default_sort=[Teacher.created_at.desc(), Teacher.id.asc()],
        )

    async def count_assignments_of(self, teacher_id: uuid.UUID) -> int:
        """Courses, class sessions and assignments that still reference the teacher (all RESTRICT FKs)."""
        total = 0
        for column in (Course.teacher_id, ClassSession.teacher_id, Assignment.teacher_id):
            stmt = select(func.count()).select_from(column.class_).where(column == teacher_id)
            total += (await self._session.execute(stmt)).scalar_one()
        return total
