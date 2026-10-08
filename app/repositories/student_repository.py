import uuid

from sqlalchemy import func, select

from app.core.pagination import Page, PageParams
from app.models.enums import StudentStatus
from app.models.student import Student
from app.models.user import User
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    model = Student

    async def get_by_user_id(self, user_id: uuid.UUID) -> Student | None:
        return await self.get_by(user_id=user_id)

    async def get_fresh(self, student_id: uuid.UUID) -> Student | None:
        """Load the student (and its eagerly-loaded user) from the DB, overwriting any stale identity-map state."""
        stmt = select(Student).where(Student.id == student_id).execution_options(populate_existing=True)
        return (await self._session.execute(stmt)).scalars().first()

    async def student_id_taken(self, student_id: str, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(func.count()).select_from(Student).where(Student.student_id == student_id)
        if exclude_id is not None:
            stmt = stmt.where(Student.id != exclude_id)
        return (await self._session.execute(stmt)).scalar_one() > 0

    async def search(
        self,
        params: PageParams,
        department_id: uuid.UUID | None = None,
        semester: int | None = None,
        status: StudentStatus | None = None,
        only_id: uuid.UUID | None = None,
    ) -> Page[Student]:
        stmt = select(Student).join(User, Student.user_id == User.id)
        if only_id is not None:
            stmt = stmt.where(Student.id == only_id)
        if department_id is not None:
            stmt = stmt.where(Student.department_id == department_id)
        if semester is not None:
            stmt = stmt.where(Student.semester == semester)
        if status is not None:
            stmt = stmt.where(Student.status == status)
        clause = self.search_clause(
            params.search,
            [User.first_name, User.last_name, User.email, Student.student_id],
        )
        if clause is not None:
            stmt = stmt.where(clause)
        return await self.paginate(
            stmt,
            params,
            sortable={
                "id": Student.id,
                "studentId": Student.student_id,
                "semester": Student.semester,
                "status": Student.status,
                "createdAt": Student.created_at,
            },
            default_sort=[Student.created_at.desc(), Student.id.asc()],
        )
