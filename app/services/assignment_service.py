"""Assignment use-cases with role scoping (students see only PUBLISHED work of courses they are enrolled in)."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.assignment import Assignment
from app.models.enums import AssignmentStatus
from app.repositories.assignment_repository import AssignmentFilters, AssignmentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)


def _aware(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so they can be stored in a timezone-aware column."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AssignmentService:
    def __init__(self, session: AsyncSession, access: AccessService) -> None:
        self._session = session
        self._access = access
        self._assignments = AssignmentRepository(session)
        self._teachers = TeacherRepository(session)

    async def list_assignments(
        self,
        principal: Principal,
        params: PageParams,
        *,
        course_id: uuid.UUID | None = None,
        status: AssignmentStatus | None = None,
        search: str | None = None,
    ) -> Page[Assignment]:
        restrict_courses: list[uuid.UUID] | None = None
        published_only = False
        if principal.is_teacher:
            restrict_courses = list(await self._access.teacher_course_ids(principal))
        elif principal.is_student:
            student_id = await self._access.student_id_for(principal)
            restrict_courses = await self._assignments.active_course_ids_for_student(student_id)
            published_only = True
        elif not principal.is_admin:
            raise ForbiddenError("You do not have access to assignments")
        filters = AssignmentFilters(
            course_id=course_id,
            status=status,
            search=search,
            restrict_course_ids=restrict_courses,
            published_only=published_only,
        )
        return await self._assignments.search(params, filters)

    async def get_assignment(self, principal: Principal, assignment_id: uuid.UUID) -> Assignment:
        assignment = await self._get_or_404(assignment_id)
        if principal.is_admin:
            return assignment
        if principal.is_teacher and assignment.course_id in await self._access.teacher_course_ids(principal):
            return assignment
        if principal.is_student and assignment.status is AssignmentStatus.PUBLISHED:
            student_id = await self._access.student_id_for(principal)
            if assignment.course_id in await self._assignments.active_course_ids_for_student(student_id):
                return assignment
        raise ForbiddenError("You do not have access to this assignment")

    async def create(self, principal: Principal, data: AssignmentCreate) -> Assignment:
        await self._access.assert_can_manage_course(principal, data.course_id)
        await self._check_teacher(principal, data.teacher_id)
        assignment = Assignment(
            title=data.title,
            description=data.description,
            course_id=data.course_id,
            teacher_id=data.teacher_id,
            due_date=_aware(data.due_date),
            max_marks=data.max_marks,
            status=data.status,
        )
        await self._assignments.add(assignment)
        await self._session.commit()
        await self._session.refresh(assignment)
        logger.info("assignment created", extra={"assignmentId": str(assignment.id)})
        return assignment

    async def update(self, principal: Principal, assignment_id: uuid.UUID, data: AssignmentUpdate) -> Assignment:
        assignment = await self._get_or_404(assignment_id)
        await self._access.assert_can_manage_course(principal, assignment.course_id)
        if data.course_id is not None and data.course_id != assignment.course_id:
            await self._access.assert_can_manage_course(principal, data.course_id)
            assignment.course_id = data.course_id
        if data.teacher_id is not None and data.teacher_id != assignment.teacher_id:
            await self._check_teacher(principal, data.teacher_id)
            assignment.teacher_id = data.teacher_id
        if data.title is not None:
            assignment.title = data.title
        if "description" in data.model_fields_set:
            assignment.description = data.description
        if data.due_date is not None:
            assignment.due_date = _aware(data.due_date)
        if data.max_marks is not None:
            assignment.max_marks = data.max_marks
        if data.status is not None:
            assignment.status = data.status
        await self._assignments.flush()
        await self._session.commit()
        await self._session.refresh(assignment)
        logger.info("assignment updated", extra={"assignmentId": str(assignment.id)})
        return assignment

    async def delete(self, principal: Principal, assignment_id: uuid.UUID) -> None:
        assignment = await self._get_or_404(assignment_id)
        await self._access.assert_can_manage_course(principal, assignment.course_id)
        await self._assignments.delete(assignment)
        await self._session.commit()
        logger.info("assignment deleted", extra={"assignmentId": str(assignment_id)})

    async def _get_or_404(self, assignment_id: uuid.UUID) -> Assignment:
        assignment = await self._assignments.get(assignment_id)
        if assignment is None:
            raise NotFoundError("Assignment not found")
        return assignment

    async def _check_teacher(self, principal: Principal, teacher_id: uuid.UUID) -> None:
        """A TEACHER may only assign work to themselves; the referenced teacher must exist."""
        if principal.is_teacher and teacher_id != await self._access.teacher_id_for(principal):
            raise ForbiddenError("Teachers can only create assignments under their own profile")
        if await self._teachers.get(teacher_id) is None:
            raise NotFoundError("Teacher not found")
