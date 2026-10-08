"""Dashboard DTOs (read-only computed views)."""

import datetime as dt
import uuid

from app.models.enums import AttendanceStatus, EnrollmentStatus
from app.schemas.base import CamelModel


class PendingItems(CamelModel):
    draft_assignments: int
    unread_notifications: int


class AdminDashboardResponse(CamelModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_departments: int
    total_courses: int
    total_enrollments: int
    active_enrollments: int
    inactive_users: int
    pending_items: PendingItems


class TeacherCourseSummary(CamelModel):
    id: uuid.UUID
    course_code: str
    course_name: str
    enrolled_students: int


class RecentAttendanceItem(CamelModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    date: dt.date
    status: AttendanceStatus


class TeacherDashboardResponse(CamelModel):
    assigned_courses: list[TeacherCourseSummary]
    total_students_enrolled: int
    average_grade: float | None
    recent_attendance: list[RecentAttendanceItem]


class StudentCourseSummary(CamelModel):
    id: uuid.UUID
    course_code: str
    course_name: str
    credits: int
    status: EnrollmentStatus


class StudentGradeSummary(CamelModel):
    course_id: uuid.UUID
    course_name: str
    marks: float
    max_marks: float
    grade: str


class AttendanceSummary(CamelModel):
    total: int
    present: int
    absent: int
    late: int
    excused: int
    attendance_percentage: float


class AssignmentDueItem(CamelModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID
    due_date: dt.datetime
    max_marks: float


class StudentDashboardResponse(CamelModel):
    enrolled_courses: list[StudentCourseSummary]
    current_grades: list[StudentGradeSummary]
    attendance_summary: AttendanceSummary
    assignments_due: list[AssignmentDueItem]
