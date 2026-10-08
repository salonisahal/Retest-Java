import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.enrollment import Enrollment
from app.models.enums import EnrollmentStatus
from app.repositories.course_repository import CourseRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.enrollment import EnrollmentRequest
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)


class EnrollmentService:
    def __init__(
        self,
        session: AsyncSession,
        enrollments: EnrollmentRepository,
        courses: CourseRepository,
        students: StudentRepository,
        access: AccessService,
    ) -> None:
        self._session = session
        self._enrollments = enrollments
        self._courses = courses
        self._students = students
        self._access = access

    async def list_enrollments(
        self,
        principal: Principal,
        params: PageParams,
        student_id: uuid.UUID | None,
        course_id: uuid.UUID | None,
        semester: int | None,
        status: EnrollmentStatus | None,
    ) -> Page[Enrollment]:
        scope_student_id: uuid.UUID | None = None
        scope_course_ids: set[uuid.UUID] | None = None
        if principal.is_student:
            scope_student_id = await self._access.student_id_for(principal)
        elif principal.is_teacher:
            scope_course_ids = await self._access.teacher_course_ids(principal)
        return await self._enrollments.search(
            params, student_id, course_id, semester, status, scope_student_id, scope_course_ids
        )

    async def get_enrollment(self, principal: Principal, enrollment_id: uuid.UUID) -> Enrollment:
        enrollment = await self._get(enrollment_id)
        if principal.is_student:
            if enrollment.student_id != await self._access.student_id_for(principal):
                raise ForbiddenError("You can only view your own enrollments")
        elif principal.is_teacher and enrollment.course_id not in await self._access.teacher_course_ids(principal):
            raise ForbiddenError("You can only view enrollments for courses you teach")
        return enrollment

    async def create_enrollment(self, principal: Principal, request: EnrollmentRequest) -> Enrollment:
        if principal.is_student and request.student_id != await self._access.student_id_for(principal):
            raise ForbiddenError("Students can only enroll themselves")
        await self._ensure_references(request)
        if principal.is_teacher:
            await self._access.assert_can_manage_course(principal, request.course_id)
        if await self._enrollments.get_by_unique_key(request.student_id, request.course_id, request.semester):
            raise ConflictError("Student is already enrolled in this course for the given semester")
        enrollment = Enrollment(
            student_id=request.student_id,
            course_id=request.course_id,
            semester=request.semester,
            # self-enrolling students always start ACTIVE
            status=EnrollmentStatus.ACTIVE if principal.is_student else request.status,
        )
        await self._enrollments.add(enrollment)
        await self._session.commit()
        logger.info("enrollment created", extra={"enrollmentId": str(enrollment.id)})
        return enrollment

    async def update_enrollment(
        self, principal: Principal, enrollment_id: uuid.UUID, request: EnrollmentRequest
    ) -> Enrollment:
        enrollment = await self._get(enrollment_id)
        await self._access.assert_can_manage_course(principal, enrollment.course_id)
        if request.course_id != enrollment.course_id:
            await self._access.assert_can_manage_course(principal, request.course_id)
        await self._ensure_references(request)
        existing = await self._enrollments.get_by_unique_key(request.student_id, request.course_id, request.semester)
        if existing is not None and existing.id != enrollment.id:
            raise ConflictError("Student is already enrolled in this course for the given semester")
        enrollment.student_id = request.student_id
        enrollment.course_id = request.course_id
        enrollment.semester = request.semester
        enrollment.status = request.status
        await self._enrollments.flush()
        await self._session.commit()
        logger.info("enrollment updated", extra={"enrollmentId": str(enrollment.id)})
        return enrollment

    async def delete_enrollment(self, principal: Principal, enrollment_id: uuid.UUID) -> None:
        enrollment = await self._get(enrollment_id)
        await self._access.assert_can_manage_course(principal, enrollment.course_id)
        await self._enrollments.delete(enrollment)
        await self._session.commit()
        logger.info("enrollment deleted", extra={"enrollmentId": str(enrollment_id)})

    async def _get(self, enrollment_id: uuid.UUID) -> Enrollment:
        enrollment = await self._enrollments.get(enrollment_id)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        return enrollment

    async def _ensure_references(self, request: EnrollmentRequest) -> None:
        if await self._students.get(request.student_id) is None:
            raise NotFoundError("Student not found")
        if await self._courses.get(request.course_id) is None:
            raise NotFoundError("Course not found")
