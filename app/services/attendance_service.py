"""Attendance use-cases with role-based scoping (ADMIN all, TEACHER own courses, STUDENT own records)."""

import datetime as dt
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus
from app.repositories.attendance_repository import AttendanceFilters, AttendanceRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)

_DUPLICATE_MESSAGE = "Attendance already recorded for this student, course and date"


class AttendanceService:
    def __init__(self, session: AsyncSession, access: AccessService) -> None:
        self._session = session
        self._access = access
        self._attendance = AttendanceRepository(session)
        self._students = StudentRepository(session)

    # ------------------------------------------------------------------ queries

    async def list_attendance(
        self,
        principal: Principal,
        params: PageParams,
        *,
        student_id: uuid.UUID | None = None,
        course_id: uuid.UUID | None = None,
        status: AttendanceStatus | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> Page[Attendance]:
        restrict_courses: list[uuid.UUID] | None = None
        restrict_student: uuid.UUID | None = None
        if principal.is_teacher:
            restrict_courses = list(await self._access.teacher_course_ids(principal))
        elif principal.is_student:
            restrict_student = await self._access.student_id_for(principal)
        elif not principal.is_admin:
            raise ForbiddenError("You do not have access to attendance records")
        filters = AttendanceFilters(
            student_id=student_id,
            course_id=course_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            restrict_course_ids=restrict_courses,
            restrict_student_id=restrict_student,
        )
        return await self._attendance.search(params, filters)

    async def get_attendance(self, principal: Principal, attendance_id: uuid.UUID) -> Attendance:
        record = await self._get_or_404(attendance_id)
        await self._ensure_can_view(principal, record)
        return record

    async def list_for_student(
        self,
        principal: Principal,
        student_id: uuid.UUID,
        params: PageParams,
        *,
        course_id: uuid.UUID | None = None,
        status: AttendanceStatus | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> Page[Attendance]:
        restrict_courses: list[uuid.UUID] | None = None
        if principal.is_student:
            if student_id != await self._access.student_id_for(principal):
                raise ForbiddenError("You can only view your own attendance")
        elif principal.is_teacher:
            restrict_courses = list(await self._access.teacher_course_ids(principal))
        elif not principal.is_admin:
            raise ForbiddenError("You do not have access to attendance records")
        if await self._students.get(student_id) is None:
            raise NotFoundError("Student not found")
        filters = AttendanceFilters(
            student_id=student_id,
            course_id=course_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            restrict_course_ids=restrict_courses,
        )
        return await self._attendance.search(params, filters)

    async def list_for_course(
        self,
        principal: Principal,
        course_id: uuid.UUID,
        params: PageParams,
        *,
        student_id: uuid.UUID | None = None,
        status: AttendanceStatus | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> Page[Attendance]:
        # 404 when the course is missing; 403 for students and for teachers of other courses.
        await self._access.assert_can_manage_course(principal, course_id)
        filters = AttendanceFilters(
            student_id=student_id, course_id=course_id, status=status, date_from=date_from, date_to=date_to
        )
        return await self._attendance.search(params, filters)

    # ------------------------------------------------------------------ commands

    async def create(self, principal: Principal, data: AttendanceCreate) -> Attendance:
        await self._access.assert_can_manage_course(principal, data.course_id)
        if await self._students.get(data.student_id) is None:
            raise NotFoundError("Student not found")
        if await self._attendance.find_duplicate(data.student_id, data.course_id, data.date) is not None:
            raise ConflictError(_DUPLICATE_MESSAGE)
        record = Attendance(
            student_id=data.student_id,
            course_id=data.course_id,
            date=data.date,
            status=data.status,
            marked_by=principal.user_id,
        )
        await self._attendance.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        logger.info("attendance marked", extra={"attendanceId": str(record.id), "courseId": str(record.course_id)})
        return record

    async def update(self, principal: Principal, attendance_id: uuid.UUID, data: AttendanceUpdate) -> Attendance:
        record = await self._get_or_404(attendance_id)
        await self._access.assert_can_manage_course(principal, record.course_id)
        if data.date is not None and data.date != record.date:
            duplicate = await self._attendance.find_duplicate(
                record.student_id, record.course_id, data.date, exclude_id=record.id
            )
            if duplicate is not None:
                raise ConflictError(_DUPLICATE_MESSAGE)
            record.date = data.date
        if data.status is not None:
            record.status = data.status
        record.marked_by = principal.user_id
        await self._attendance.flush()
        await self._session.commit()
        await self._session.refresh(record)
        logger.info("attendance updated", extra={"attendanceId": str(record.id)})
        return record

    # ------------------------------------------------------------------ helpers

    async def _get_or_404(self, attendance_id: uuid.UUID) -> Attendance:
        record = await self._attendance.get(attendance_id)
        if record is None:
            raise NotFoundError("Attendance record not found")
        return record

    async def _ensure_can_view(self, principal: Principal, record: Attendance) -> None:
        if principal.is_admin:
            return
        if principal.is_teacher and record.course_id in await self._access.teacher_course_ids(principal):
            return
        if principal.is_student and record.student_id == await self._access.student_id_for(principal):
            return
        raise ForbiddenError("You do not have access to this attendance record")
