"""Grade use-cases with role-based scoping; the letter grade is always computed server-side."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.grade import Grade
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.grade_repository import GradeFilters, GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.grade import GradeCreate, GradeUpdate
from app.services.access_service import AccessService
from app.services.grade_calculator import calculate_grade_letter

logger = logging.getLogger(__name__)


class GradeService:
    def __init__(self, session: AsyncSession, access: AccessService) -> None:
        self._session = session
        self._access = access
        self._grades = GradeRepository(session)
        self._students = StudentRepository(session)
        self._assignments = AssignmentRepository(session)

    async def list_grades(
        self,
        principal: Principal,
        params: PageParams,
        *,
        student_id: uuid.UUID | None = None,
        course_id: uuid.UUID | None = None,
        assignment_id: uuid.UUID | None = None,
    ) -> Page[Grade]:
        restrict_courses: list[uuid.UUID] | None = None
        restrict_student: uuid.UUID | None = None
        if principal.is_teacher:
            restrict_courses = list(await self._access.teacher_course_ids(principal))
        elif principal.is_student:
            restrict_student = await self._access.student_id_for(principal)
        elif not principal.is_admin:
            raise ForbiddenError("You do not have access to grades")
        filters = GradeFilters(
            student_id=student_id,
            course_id=course_id,
            assignment_id=assignment_id,
            restrict_course_ids=restrict_courses,
            restrict_student_id=restrict_student,
        )
        return await self._grades.search(params, filters)

    async def get_grade(self, principal: Principal, grade_id: uuid.UUID) -> Grade:
        grade = await self._get_or_404(grade_id)
        if principal.is_admin:
            return grade
        if principal.is_teacher and grade.course_id in await self._access.teacher_course_ids(principal):
            return grade
        if principal.is_student and grade.student_id == await self._access.student_id_for(principal):
            return grade
        raise ForbiddenError("You do not have access to this grade")

    async def create(self, principal: Principal, data: GradeCreate) -> Grade:
        await self._access.assert_can_manage_course(principal, data.course_id)
        if await self._students.get(data.student_id) is None:
            raise NotFoundError("Student not found")
        if data.assignment_id is not None:
            await self._ensure_assignment_in_course(data.assignment_id, data.course_id)
        grade = Grade(
            student_id=data.student_id,
            course_id=data.course_id,
            assignment_id=data.assignment_id,
            marks=data.marks,
            max_marks=data.max_marks,
            grade=calculate_grade_letter(data.marks, data.max_marks),
        )
        await self._grades.add(grade)
        await self._session.commit()
        await self._session.refresh(grade)
        logger.info("grade recorded", extra={"gradeId": str(grade.id), "letter": grade.grade})
        return grade

    async def update(self, principal: Principal, grade_id: uuid.UUID, data: GradeUpdate) -> Grade:
        grade = await self._get_or_404(grade_id)
        await self._access.assert_can_manage_course(principal, grade.course_id)

        marks = data.marks if data.marks is not None else grade.marks
        max_marks = data.max_marks if data.max_marks is not None else grade.max_marks
        if marks > max_marks:
            raise ValidationFailedError(errors={"marks": ["marks must not exceed maxMarks"]})

        if "assignment_id" in data.model_fields_set:
            if data.assignment_id is not None:
                await self._ensure_assignment_in_course(data.assignment_id, grade.course_id)
            grade.assignment_id = data.assignment_id
        grade.marks = marks
        grade.max_marks = max_marks
        grade.grade = calculate_grade_letter(marks, max_marks)
        await self._grades.flush()
        await self._session.commit()
        await self._session.refresh(grade)
        logger.info("grade updated", extra={"gradeId": str(grade.id), "letter": grade.grade})
        return grade

    async def delete(self, principal: Principal, grade_id: uuid.UUID) -> None:
        grade = await self._get_or_404(grade_id)
        await self._access.assert_can_manage_course(principal, grade.course_id)
        await self._grades.delete(grade)
        await self._session.commit()
        logger.info("grade deleted", extra={"gradeId": str(grade_id)})

    async def _get_or_404(self, grade_id: uuid.UUID) -> Grade:
        grade = await self._grades.get(grade_id)
        if grade is None:
            raise NotFoundError("Grade not found")
        return grade

    async def _ensure_assignment_in_course(self, assignment_id: uuid.UUID, course_id: uuid.UUID) -> None:
        assignment = await self._assignments.get(assignment_id)
        if assignment is None:
            raise NotFoundError("Assignment not found")
        if assignment.course_id != course_id:
            raise ValidationFailedError(errors={"assignmentId": ["Assignment does not belong to the given course"]})
