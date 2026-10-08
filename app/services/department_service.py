"""Department business logic."""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page, PageParams
from app.models.department import Department
from app.repositories.department_repository import DepartmentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.department import DepartmentCreateRequest, DepartmentUpdateRequest

logger = logging.getLogger(__name__)


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._departments = DepartmentRepository(session)
        self._teachers = TeacherRepository(session)

    async def list(self, params: PageParams) -> Page[Department]:
        return await self._departments.search(params)

    async def get(self, department_id: uuid.UUID) -> Department:
        department = await self._departments.get(department_id)
        if department is None:
            raise NotFoundError("Department not found")
        return department

    async def create(self, request: DepartmentCreateRequest) -> Department:
        await self._assert_unique(request.name, request.code)
        await self._assert_teacher_exists(request.head_teacher_id)
        department = Department(name=request.name, code=request.code, head_teacher_id=request.head_teacher_id)
        await self._departments.add(department)
        await self._session.commit()
        logger.info("department created", extra={"departmentId": str(department.id)})
        return department

    async def update(self, department_id: uuid.UUID, request: DepartmentUpdateRequest) -> Department:
        department = await self.get(department_id)
        await self._assert_unique(request.name, request.code, exclude_id=department_id)
        await self._assert_teacher_exists(request.head_teacher_id)
        department.name = request.name
        department.code = request.code
        department.head_teacher_id = request.head_teacher_id
        await self._departments.flush()
        await self._session.commit()
        logger.info("department updated", extra={"departmentId": str(department_id)})
        return department

    async def delete(self, department_id: uuid.UUID) -> None:
        department = await self.get(department_id)
        references = await self._departments.count_references(department_id)
        in_use = [f"{count} {label}" for label, count in references.items() if count]
        if in_use:
            raise ConflictError(f"Department cannot be deleted while it is referenced by {', '.join(in_use)}")
        try:
            await self._departments.delete(department)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError("Department cannot be deleted because other records reference it") from exc
        logger.info("department deleted", extra={"departmentId": str(department_id)})

    async def _assert_unique(self, name: str, code: str, exclude_id: uuid.UUID | None = None) -> None:
        if await self._departments.name_taken(name, exclude_id):
            raise ConflictError("A department with this name already exists")
        if await self._departments.code_taken(code, exclude_id):
            raise ConflictError("A department with this code already exists")

    async def _assert_teacher_exists(self, teacher_id: uuid.UUID | None) -> None:
        if teacher_id is not None and await self._teachers.get(teacher_id) is None:
            raise NotFoundError("Teacher not found")
