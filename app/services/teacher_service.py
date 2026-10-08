"""Teacher business logic: a teacher is a TEACHER user plus a profile, always written in one transaction."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.security import hash_password
from app.models.enums import UserRole, UserStatus
from app.models.teacher import Teacher
from app.models.user import User
from app.repositories.department_repository import DepartmentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.schemas.teacher import TeacherCreateRequest, TeacherUpdateRequest

logger = logging.getLogger(__name__)


class TeacherService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._teachers = TeacherRepository(session)
        self._users = UserRepository(session)
        self._departments = DepartmentRepository(session)

    async def list(self, params: PageParams, department_id: uuid.UUID | None = None) -> Page[Teacher]:
        return await self._teachers.search(params, department_id)

    async def get(self, teacher_id: uuid.UUID) -> Teacher:
        teacher = await self._teachers.get(teacher_id)
        if teacher is None:
            raise NotFoundError("Teacher not found")
        return teacher

    async def create(self, request: TeacherCreateRequest) -> Teacher:
        email = str(request.email).lower()
        await self._assert_department_exists(request.department_id)
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("A user with this email already exists")
        if await self._teachers.employee_id_taken(request.employee_id):
            raise ConflictError("A teacher with this employee ID already exists")

        user = User(
            first_name=request.first_name,
            last_name=request.last_name,
            email=email,
            password_hash=hash_password(request.password),
            phone=request.phone,
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        await self._users.add(user)
        teacher = Teacher(
            user_id=user.id,
            employee_id=request.employee_id,
            department_id=request.department_id,
            specialization=request.specialization,
            status=request.status,
        )
        teacher.user = user
        await self._teachers.add(teacher)
        await self._session.commit()
        logger.info("teacher created", extra={"teacherId": str(teacher.id)})
        return teacher

    async def update(self, teacher_id: uuid.UUID, request: TeacherUpdateRequest) -> Teacher:
        teacher = await self.get(teacher_id)
        user = teacher.user
        email = str(request.email).lower()
        await self._assert_department_exists(request.department_id)
        existing = await self._users.get_by_email(email)
        if existing is not None and existing.id != user.id:
            raise ConflictError("A user with this email already exists")
        if await self._teachers.employee_id_taken(request.employee_id, exclude_id=teacher_id):
            raise ConflictError("A teacher with this employee ID already exists")

        user.first_name = request.first_name
        user.last_name = request.last_name
        user.email = email
        user.phone = request.phone
        teacher.employee_id = request.employee_id
        teacher.department_id = request.department_id
        teacher.specialization = request.specialization
        teacher.status = request.status
        await self._teachers.flush()
        await self._session.commit()
        logger.info("teacher updated", extra={"teacherId": str(teacher_id)})
        return await self._fresh(teacher_id)

    async def delete(self, teacher_id: uuid.UUID) -> None:
        teacher = await self.get(teacher_id)
        if await self._teachers.count_assignments_of(teacher_id):
            raise ConflictError("Teacher cannot be deleted while still assigned to courses, classes or assignments")
        user = teacher.user
        try:
            await self._teachers.delete(teacher)
            await self._users.delete(user)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError("Teacher cannot be deleted because other records reference it") from exc
        logger.info("teacher deleted", extra={"teacherId": str(teacher_id)})

    async def _fresh(self, teacher_id: uuid.UUID) -> Teacher:
        teacher = await self._teachers.get_fresh(teacher_id)
        if teacher is None:  # pragma: no cover - only if deleted concurrently
            raise NotFoundError("Teacher not found")
        return teacher

    async def _assert_department_exists(self, department_id: uuid.UUID) -> None:
        if await self._departments.get(department_id) is None:
            raise NotFoundError("Department not found")
