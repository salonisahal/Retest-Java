"""Dashboard use-cases: role-specific, read-only summaries computed with SQL aggregates."""

from datetime import UTC, datetime

from app.core.principal import Principal
from app.models.enums import AttendanceStatus
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    AdminDashboardResponse,
    AssignmentDueItem,
    AttendanceSummary,
    PendingItems,
    RecentAttendanceItem,
    StudentCourseSummary,
    StudentDashboardResponse,
    StudentGradeSummary,
    TeacherCourseSummary,
    TeacherDashboardResponse,
)
from app.services.access_service import AccessService


class DashboardService:
    def __init__(self, repository: DashboardRepository, access: AccessService) -> None:
        self._repo = repository
        self._access = access

    async def admin(self, principal: Principal) -> AdminDashboardResponse:
        row = await self._repo.admin_totals(principal.user_id)
        return AdminDashboardResponse(
            total_users=row.total_users,
            total_students=row.total_students,
            total_teachers=row.total_teachers,
            total_departments=row.total_departments,
            total_courses=row.total_courses,
            total_enrollments=row.total_enrollments,
            active_enrollments=row.active_enrollments,
            inactive_users=row.inactive_users,
            pending_items=PendingItems(
                draft_assignments=row.draft_assignments, unread_notifications=row.unread_notifications
            ),
        )

    async def teacher(self, principal: Principal) -> TeacherDashboardResponse:
        teacher_id = await self._access.teacher_id_for(principal)
        courses = await self._repo.teacher_courses_with_counts(teacher_id)
        total_students = await self._repo.teacher_distinct_active_students(teacher_id)
        average = await self._repo.teacher_average_grade_percentage(teacher_id)
        attendance = await self._repo.teacher_recent_attendance(teacher_id, limit=10)
        return TeacherDashboardResponse(
            assigned_courses=[
                TeacherCourseSummary(
                    id=c.id,
                    course_code=c.course_code,
                    course_name=c.course_name,
                    enrolled_students=c.enrolled_students,
                )
                for c in courses
            ],
            total_students_enrolled=total_students,
            average_grade=round(average, 2) if average is not None else None,
            recent_attendance=[
                RecentAttendanceItem(
                    id=a.id, student_id=a.student_id, course_id=a.course_id, date=a.date, status=a.status
                )
                for a in attendance
            ],
        )

    async def student(self, principal: Principal) -> StudentDashboardResponse:
        student_id = await self._access.student_id_for(principal)
        courses = await self._repo.student_enrolled_courses(student_id)
        grades = await self._repo.student_grades(student_id)
        counts = await self._repo.student_attendance_counts(student_id)
        due = await self._repo.student_assignments_due(student_id, datetime.now(UTC), limit=10)

        present = counts.get(AttendanceStatus.PRESENT, 0)
        late = counts.get(AttendanceStatus.LATE, 0)
        total = sum(counts.values())
        # Attendance percentage counts PRESENT and LATE as attended; EXCUSED/ABSENT do not.
        percentage = round((present + late) / total * 100, 2) if total else 0.0

        return StudentDashboardResponse(
            enrolled_courses=[
                StudentCourseSummary(
                    id=c.id, course_code=c.course_code, course_name=c.course_name, credits=c.credits, status=c.status
                )
                for c in courses
            ],
            current_grades=[
                StudentGradeSummary(
                    course_id=g.course_id,
                    course_name=g.course_name,
                    marks=g.marks,
                    max_marks=g.max_marks,
                    grade=g.grade,
                )
                for g in grades
            ],
            attendance_summary=AttendanceSummary(
                total=total,
                present=present,
                absent=counts.get(AttendanceStatus.ABSENT, 0),
                late=late,
                excused=counts.get(AttendanceStatus.EXCUSED, 0),
                attendance_percentage=percentage,
            ),
            assignments_due=[
                AssignmentDueItem(
                    id=a.id, title=a.title, course_id=a.course_id, due_date=a.due_date, max_marks=a.max_marks
                )
                for a in due
            ],
        )
