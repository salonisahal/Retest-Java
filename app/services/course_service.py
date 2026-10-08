import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.course import Course
from app.repositories.course_repository import CourseRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.course import CourseRequest
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)


class CourseService:
    def __init__(
        self,
        session: AsyncSession,
        courses: CourseRepository,
        departments: DepartmentRepository,
        teachers: TeacherRepository,
        access: AccessService,
    ) -> None:
        self._session = session
        self._courses = courses
        self._departments = departments
        self._teachers = teachers
        self._access = access

    async def list_courses(
        self,
        params: PageParams,
        department_id: uuid.UUID | None,
        teacher_id: uuid.UUID | None,
        semester: int | None,
    ) -> Page[Course]:
        return await self._courses.search(params, department_id, teacher_id, semester)

    async def get_course(self, course_id: uuid.UUID) -> Course:
        course = await self._courses.get(course_id)
        if course is None:
            raise NotFoundError("Course not found")
        return course

    async def create_course(self, request: CourseRequest) -> Course:
        await self._ensure_references(request)
        if await self._courses.get_by_code(request.course_code) is not None:
            raise ConflictError(f"Course code '{request.course_code}' already exists")
        course = Course(
            course_code=request.course_code,
            course_name=request.course_name,
            credits=request.credits,
            department_id=request.department_id,
            teacher_id=request.teacher_id,
            semester=request.semester,
        )
        await self._courses.add(course)
        await self._session.commit()
        logger.info("course created", extra={"courseId": str(course.id)})
        return course

    async def update_course(self, principal: Principal, course_id: uuid.UUID, request: CourseRequest) -> Course:
        await self._access.assert_can_manage_course(principal, course_id)
        course = await self.get_course(course_id)
        if not principal.is_admin and request.teacher_id != course.teacher_id:
            raise ForbiddenError("Only an administrator can reassign the course teacher")
        await self._ensure_references(request)
        existing = await self._courses.get_by_code(request.course_code)
        if existing is not None and existing.id != course.id:
            raise ConflictError(f"Course code '{request.course_code}' already exists")
        course.course_code = request.course_code
        course.course_name = request.course_name
        course.credits = request.credits
        course.department_id = request.department_id
        course.teacher_id = request.teacher_id
        course.semester = request.semester
        await self._courses.flush()
        await self._session.commit()
        logger.info("course updated", extra={"courseId": str(course.id)})
        return course

    async def delete_course(self, principal: Principal, course_id: uuid.UUID) -> None:
        await self._access.assert_can_manage_course(principal, course_id)
        course = await self.get_course(course_id)
        await self._courses.delete(course)
        await self._session.commit()
        logger.info("course deleted", extra={"courseId": str(course_id)})

    async def _ensure_references(self, request: CourseRequest) -> None:
        if await self._departments.get(request.department_id) is None:
            raise NotFoundError("Department not found")
        if await self._teachers.get(request.teacher_id) is None:
            raise NotFoundError("Teacher not found")
