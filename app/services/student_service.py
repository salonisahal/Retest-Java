"""Student business logic: a student is a STUDENT user plus a profile, always written in one transaction."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.core.security import hash_password
from app.models.enums import StudentStatus, UserRole, UserStatus
from app.models.student import Student
from app.models.user import User
from app.repositories.department_repository import DepartmentRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.student import StudentCreateRequest, StudentUpdateRequest

logger = logging.getLogger(__name__)


class StudentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._students = StudentRepository(session)
        self._users = UserRepository(session)
        self._departments = DepartmentRepository(session)

    async def list(
        self,
        principal: Principal,
        params: PageParams,
        department_id: uuid.UUID | None = None,
        semester: int | None = None,
        status: StudentStatus | None = None,
    ) -> Page[Student]:
        """ADMIN/TEACHER see every student; a STUDENT only their own record (silently filtered)."""
        only_id: uuid.UUID | None = None
        if principal.is_student:
            own = await self._students.get_by_user_id(principal.user_id)
            if own is None:
                return Page(items=[], total=0, page=params.page, size=params.size)
            only_id = own.id
        return await self._students.search(params, department_id, semester, status, only_id)

    async def get_for(self, principal: Principal, student_id: uuid.UUID) -> Student:
        student = await self.get(student_id)
        if principal.is_student and student.user_id != principal.user_id:
            raise ForbiddenError("You can only view your own student record")
        return student

    async def get(self, student_id: uuid.UUID) -> Student:
        student = await self._students.get(student_id)
        if student is None:
            raise NotFoundError("Student not found")
        return student

    async def create(self, request: StudentCreateRequest) -> Student:
        email = str(request.email).lower()
        await self._assert_department_exists(request.department_id)
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists")
        if await self._students.student_id_taken(request.student_id):
            raise ConflictError("A student with this student ID already exists")

        user = User(
            first_name=request.first_name,
            last_name=request.last_name,
            email=email,
            password_hash=hash_password(request.password),
            phone=request.phone,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        await self._users.add(user)
        student = Student(
            user_id=user.id,
            student_id=request.student_id,
            department_id=request.department_id,
            semester=request.semester,
            status=request.status,
        )
        student.user = user
        await self._students.add(student)
        await self._session.commit()
        logger.info("student created", extra={"studentId": str(student.id)})
        return student

    async def update(self, student_id: uuid.UUID, request: StudentUpdateRequest) -> Student:
        student = await self.get(student_id)
        user = student.user
        email = str(request.email).lower()
        await self._assert_department_exists(request.department_id)
        existing = await self._users.get_by_email(email)
        if existing is not None and existing.id != user.id:
            raise ConflictError("A user with this email already exists")
        if await self._students.student_id_taken(request.student_id, exclude_id=student_id):
            raise ConflictError("A student with this student ID already exists")

        user.first_name = request.first_name
        user.last_name = request.last_name
        user.email = email
        user.phone = request.phone
        student.student_id = request.student_id
        student.department_id = request.department_id
        student.semester = request.semester
        student.status = request.status
        await self._students.flush()
        await self._session.commit()
        logger.info("student updated", extra={"studentId": str(student_id)})
        return await self._fresh(student_id)

    async def update_status(self, student_id: uuid.UUID, status: StudentStatus) -> Student:
        student = await self.get(student_id)
        student.status = status
        await self._students.flush()
        await self._session.commit()
        logger.info("student status changed", extra={"studentId": str(student_id), "status": status.value})
        return await self._fresh(student_id)

    async def delete(self, student_id: uuid.UUID) -> None:
        student = await self.get(student_id)
        user = student.user
        try:
            await self._students.delete(student)
            await self._users.delete(user)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError("Student cannot be deleted because other records reference it") from exc
        logger.info("student deleted", extra={"studentId": str(student_id)})

    async def _fresh(self, student_id: uuid.UUID) -> Student:
        student = await self._students.get_fresh(student_id)
        if student is None:  # pragma: no cover - only if deleted concurrently
            raise NotFoundError("Student not found")
        return student

    async def _assert_department_exists(self, department_id: uuid.UUID) -> None:
        if await self._departments.get(department_id) is None:
            raise NotFoundError("Department not found")
