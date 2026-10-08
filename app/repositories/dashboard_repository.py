"""Read-only aggregate queries backing the dashboards (each method issues a constant number of SQL statements)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.enums import AssignmentStatus, AttendanceStatus, EnrollmentStatus, UserStatus
from app.models.grade import Grade
from app.models.notification import Notification
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User


def _count(model: Any, *where: Any) -> Any:
    stmt = select(func.count()).select_from(model)
    if where:
        stmt = stmt.where(*where)
    return stmt.scalar_subquery()


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ admin
    async def admin_totals(self, admin_user_id: uuid.UUID) -> Row[Any]:
        """All admin counters in ONE statement (scalar subqueries)."""
        stmt = select(
            _count(User).label("total_users"),
            _count(Student).label("total_students"),
            _count(Teacher).label("total_teachers"),
            _count(Department).label("total_departments"),
            _count(Course).label("total_courses"),
            _count(Enrollment).label("total_enrollments"),
            _count(Enrollment, Enrollment.status == EnrollmentStatus.ACTIVE).label("active_enrollments"),
            _count(User, User.status == UserStatus.INACTIVE).label("inactive_users"),
            _count(Assignment, Assignment.status == AssignmentStatus.DRAFT).label("draft_assignments"),
            _count(Notification, Notification.user_id == admin_user_id, Notification.is_read.is_(False)).label(
                "unread_notifications"
            ),
        )
        return (await self._session.execute(stmt)).one()

    # ---------------------------------------------------------------- teacher
    async def teacher_courses_with_counts(self, teacher_id: uuid.UUID) -> Sequence[Row[Any]]:
        """Own courses with the number of ACTIVE enrollments (single grouped outer join)."""
        stmt = (
            select(
                Course.id,
                Course.course_code,
                Course.course_name,
                func.count(Enrollment.id).label("enrolled_students"),
            )
            .outerjoin(
                Enrollment,
                (Enrollment.course_id == Course.id) & (Enrollment.status == EnrollmentStatus.ACTIVE),
            )
            .where(Course.teacher_id == teacher_id)
            .group_by(Course.id, Course.course_code, Course.course_name)
            .order_by(Course.course_code)
        )
        return (await self._session.execute(stmt)).all()

    async def teacher_distinct_active_students(self, teacher_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(Enrollment.student_id)))
            .join(Course, Course.id == Enrollment.course_id)
            .where(Course.teacher_id == teacher_id, Enrollment.status == EnrollmentStatus.ACTIVE)
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def teacher_average_grade_percentage(self, teacher_id: uuid.UUID) -> float | None:
        stmt = (
            select(func.avg(Grade.marks / Grade.max_marks * 100.0))
            .join(Course, Course.id == Grade.course_id)
            .where(Course.teacher_id == teacher_id)
        )
        value = (await self._session.execute(stmt)).scalar_one()
        return float(value) if value is not None else None

    async def teacher_recent_attendance(self, teacher_id: uuid.UUID, limit: int = 10) -> Sequence[Attendance]:
        stmt = (
            select(Attendance)
            .join(Course, Course.id == Attendance.course_id)
            .where(Course.teacher_id == teacher_id)
            .order_by(Attendance.date.desc(), Attendance.created_at.desc(), Attendance.id)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()

    # ---------------------------------------------------------------- student
    async def student_enrolled_courses(self, student_id: uuid.UUID) -> Sequence[Row[Any]]:
        stmt = (
            select(Course.id, Course.course_code, Course.course_name, Course.credits, Enrollment.status)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == student_id)
            .order_by(Course.course_code)
        )
        return (await self._session.execute(stmt)).all()

    async def student_grades(self, student_id: uuid.UUID) -> Sequence[Row[Any]]:
        stmt = (
            select(Grade.course_id, Course.course_name, Grade.marks, Grade.max_marks, Grade.grade)
            .join(Course, Course.id == Grade.course_id)
            .where(Grade.student_id == student_id)
            .order_by(Course.course_name, Grade.created_at.desc())
        )
        return (await self._session.execute(stmt)).all()

    async def student_attendance_counts(self, student_id: uuid.UUID) -> dict[AttendanceStatus, int]:
        """Counts per attendance status in one grouped query."""
        stmt = select(Attendance.status, func.count()).where(Attendance.student_id == student_id)
        stmt = stmt.group_by(Attendance.status)
        return dict((await self._session.execute(stmt)).tuples().all())

    async def student_assignments_due(
        self, student_id: uuid.UUID, now: datetime, limit: int = 10
    ) -> Sequence[Assignment]:
        """PUBLISHED assignments of the student's ACTIVE-enrolled courses due at/after ``now``, soonest first."""
        enrolled_courses = select(Enrollment.course_id).where(
            Enrollment.student_id == student_id, Enrollment.status == EnrollmentStatus.ACTIVE
        )
        stmt = (
            select(Assignment)
            .where(
                Assignment.course_id.in_(enrolled_courses),
                Assignment.status == AssignmentStatus.PUBLISHED,
                Assignment.due_date >= now,
            )
            .order_by(Assignment.due_date.asc(), Assignment.id)
            .limit(limit)
        )
        return (await self._session.execute(stmt)).scalars().all()
