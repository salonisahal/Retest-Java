"""Import every model so Base.metadata is complete (Alembic autogenerate, tests)."""

from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.base import Base
from app.models.course import ClassSession, Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.grade import Grade
from app.models.notification import Notification
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import RefreshToken, User

__all__ = [
    "Assignment",
    "Attendance",
    "Base",
    "ClassSession",
    "Course",
    "Department",
    "Enrollment",
    "Grade",
    "Notification",
    "RefreshToken",
    "Student",
    "Teacher",
    "User",
]
