"""Resource-level authorization helpers shared by all services (teacher/student ownership checks)."""

import logging
from uuid import UUID

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.principal import Principal
from app.repositories.course_repository import CourseRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository

logger = logging.getLogger(__name__)


class AccessService:
    """Resolves the caller's teacher/student profile and enforces course ownership."""

    def __init__(
        self,
        teacher_repository: TeacherRepository,
        student_repository: StudentRepository,
        course_repository: CourseRepository,
    ) -> None:
        self._teachers = teacher_repository
        self._students = student_repository
        self._courses = course_repository

    async def teacher_id_for(self, principal: Principal) -> UUID:
        """Teacher profile id (teachers.id) of the caller; ForbiddenError when the caller has no teacher profile."""
        teacher = await self._teachers.get_by_user_id(principal.user_id)
        if teacher is None:
            raise ForbiddenError("No teacher profile is linked to this account")
        return teacher.id

    async def student_id_for(self, principal: Principal) -> UUID:
        """Student profile id (students.id) of the caller; ForbiddenError when the caller has no student profile."""
        student = await self._students.get_by_user_id(principal.user_id)
        if student is None:
            raise ForbiddenError("No student profile is linked to this account")
        return student.id

    async def teacher_course_ids(self, principal: Principal) -> set[UUID]:
        """Ids of the courses taught by the calling teacher (empty set for no profile)."""
        teacher = await self._teachers.get_by_user_id(principal.user_id)
        if teacher is None:
            return set()
        courses = await self._courses.list_ids_by_teacher(teacher.id)
        return set(courses)

    async def assert_can_manage_course(self, principal: Principal, course_id: UUID) -> None:
        """ADMIN always passes; a TEACHER only for a course they teach; anyone else is forbidden.

        Raises NotFoundError when the course does not exist, ForbiddenError when not permitted.
        """
        course = await self._courses.get(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        if principal.is_admin:
            return
        if principal.is_teacher and course.teacher_id == await self.teacher_id_for(principal):
            return
        logger.info("course access denied", extra={"courseId": str(course_id), "userId": str(principal.user_id)})
        raise ForbiddenError("You do not have permission to manage this course")
