"""Idempotent demo-data seeder.

Run with ``python -m app.seed.seed_data``. Every entity is looked up by its natural key (email, employee id,
student id, department/course code, ...) and skipped when it already exists, so the script can be run any number of
times. Each entity group is committed once.

Demo credentials (change them outside of local/dev use):
    admin@example.com        / Admin@123
    teacher1..4@example.com  / Teacher@123
    student1..24@example.com / Student@123
"""

import asyncio
import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionFactory, engine
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.course import ClassSession, Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.enums import (
    AssignmentStatus,
    AttendanceStatus,
    EnrollmentStatus,
    NotificationType,
    ScheduleDay,
    StudentStatus,
    UserRole,
    UserStatus,
)
from app.models.grade import Grade
from app.models.notification import Notification
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.services.grade_calculator import calculate_grade_letter

logger = logging.getLogger("app.seed")

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"
TEACHER_PASSWORD = "Teacher@123"
STUDENT_PASSWORD = "Student@123"

DEPARTMENTS = [
    ("CS", "Computer Science"),
    ("MATH", "Mathematics"),
    ("PHY", "Physics"),
    ("ENG", "English Literature"),
]
TEACHER_NAMES = [("Alice", "Johnson"), ("Brian", "Smith"), ("Carla", "Nguyen"), ("David", "Okafor")]
SPECIALIZATIONS = ["Software Engineering", "Applied Mathematics", "Quantum Mechanics", "Modern Literature"]

# (code suffix, name, credits, semester): three courses per department
COURSES_BY_DEPT: dict[str, list[tuple[str, str, int, int]]] = {
    "CS": [
        ("101", "Introduction to Programming", 4, 1),
        ("201", "Data Structures", 4, 2),
        ("301", "Databases", 3, 3),
    ],
    "MATH": [
        ("101", "Calculus I", 4, 1),
        ("201", "Linear Algebra", 3, 2),
        ("301", "Probability and Statistics", 3, 3),
    ],
    "PHY": [
        ("101", "Mechanics", 4, 1),
        ("201", "Electromagnetism", 4, 2),
        ("301", "Thermodynamics", 3, 3),
    ],
    "ENG": [
        ("101", "Academic Writing", 2, 1),
        ("201", "Shakespeare Studies", 3, 2),
        ("301", "Modern Novel", 3, 3),
    ],
}
STUDENT_FIRST = (
    "Emma Liam Olivia Noah Ava Elijah Sophia Lucas Isabella Mason Mia Ethan "
    "Amelia Logan Harper James Evelyn Aiden Abigail Jackson Ella Henry Grace Leo"
).split()
STUDENT_LAST = "Brown Davis Garcia Miller Wilson Moore Taylor Anderson Thomas Lee".split()
ROOMS = ["A-101", "A-102", "B-201", "B-202", "C-301"]
DAYS = [ScheduleDay.MONDAY, ScheduleDay.TUESDAY, ScheduleDay.WEDNESDAY, ScheduleDay.THURSDAY, ScheduleDay.FRIDAY]
ATTENDANCE_PATTERN = [
    AttendanceStatus.PRESENT,
    AttendanceStatus.PRESENT,
    AttendanceStatus.LATE,
    AttendanceStatus.PRESENT,
    AttendanceStatus.ABSENT,
    AttendanceStatus.EXCUSED,
    AttendanceStatus.PRESENT,
]
STUDENT_COUNT = len(STUDENT_FIRST)

# (title, message, type, is_read) per role
ADMIN_NOTIFICATIONS = [
    ("Welcome, Administrator", "The student management system is ready.", NotificationType.INFO, True),
    ("Draft assignments pending", "Some assignments are still in DRAFT.", NotificationType.WARNING, False),
    ("New term started", "Review department and course setup.", NotificationType.ALERT, False),
]
TEACHER_NOTIFICATIONS = [
    ("Welcome, Teacher", "Your courses have been assigned.", NotificationType.INFO, True),
    ("Attendance reminder", "Please record this week's attendance.", NotificationType.ATTENDANCE, False),
]
STUDENT_NOTIFICATIONS = [
    ("Welcome, Student", "You have been enrolled in your courses.", NotificationType.INFO, True),
    ("Assignment published", "A new assignment is available.", NotificationType.ASSIGNMENT, False),
    ("Grade posted", "A new grade has been posted.", NotificationType.GRADE, False),
]


class _PasswordCache:
    """Hash each distinct password at most once (bcrypt is deliberately slow) and only when actually needed."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, password: str) -> str:
        if password not in self._cache:
            self._cache[password] = hash_password(password)
        return self._cache[password]


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


async def _existing(session: AsyncSession, *columns: Any) -> set[Any]:
    """Set of existing natural-key values (a scalar, or a tuple when several columns are given)."""
    rows = (await session.execute(select(*columns))).all()
    return {row[0] if len(columns) == 1 else tuple(row) for row in rows}


async def _user_by_email(session: AsyncSession, email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def _seed_people(session: AsyncSession, passwords: _PasswordCache) -> dict[str, int]:
    """Admin, departments, teachers (+ department heads) and students."""
    created = {"users": 0, "departments": 0, "teachers": 0, "students": 0}

    if await _user_by_email(session, ADMIN_EMAIL) is None:
        session.add(
            User(
                first_name="System",
                last_name="Administrator",
                email=ADMIN_EMAIL,
                password_hash=passwords.get(ADMIN_PASSWORD),
                phone="+10000000000",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
        )
        created["users"] += 1

    existing_codes = await _existing(session, Department.code)
    for code, name in DEPARTMENTS:
        if code not in existing_codes:
            session.add(Department(code=code, name=name))
            created["departments"] += 1
    await session.flush()
    departments = {d.code: d for d in (await session.execute(select(Department))).scalars()}

    existing_employee_ids = await _existing(session, Teacher.employee_id)
    for i, (dept_code, _) in enumerate(DEPARTMENTS, start=1):
        employee_id = f"EMP{i:04d}"
        if employee_id in existing_employee_ids:
            continue
        email = f"teacher{i}@example.com"
        user = await _user_by_email(session, email)
        if user is None:
            first, last = TEACHER_NAMES[i - 1]
            user = User(
                first_name=first,
                last_name=last,
                email=email,
                password_hash=passwords.get(TEACHER_PASSWORD),
                phone=f"+1555000{i:04d}",
                role=UserRole.TEACHER,
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.flush()
            created["users"] += 1
        session.add(
            Teacher(
                user_id=user.id,
                employee_id=employee_id,
                department_id=departments[dept_code].id,
                specialization=SPECIALIZATIONS[i - 1],
                status="ACTIVE",
            )
        )
        created["teachers"] += 1
    await session.flush()

    # head teacher of each department = the teacher assigned to it (only when no head is set yet)
    teacher_by_employee = {t.employee_id: t for t in (await session.execute(select(Teacher))).scalars()}
    for i, (dept_code, _) in enumerate(DEPARTMENTS, start=1):
        head = teacher_by_employee.get(f"EMP{i:04d}")
        if departments[dept_code].head_teacher_id is None and head is not None:
            departments[dept_code].head_teacher_id = head.id

    existing_student_ids = await _existing(session, Student.student_id)
    for i in range(1, STUDENT_COUNT + 1):
        student_code = f"STU{i:04d}"
        if student_code in existing_student_ids:
            continue
        email = f"student{i}@example.com"
        user = await _user_by_email(session, email)
        if user is None:
            user = User(
                first_name=STUDENT_FIRST[i - 1],
                last_name=STUDENT_LAST[i % len(STUDENT_LAST)],
                email=email,
                password_hash=passwords.get(STUDENT_PASSWORD),
                phone=f"+1666000{i:04d}",
                role=UserRole.STUDENT,
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.flush()
            created["users"] += 1
        session.add(
            Student(
                user_id=user.id,
                student_id=student_code,
                department_id=departments[DEPARTMENTS[(i - 1) % len(DEPARTMENTS)][0]].id,
                semester=1 + (i - 1) % 3,
                status=StudentStatus.ACTIVE,
            )
        )
        created["students"] += 1

    await session.commit()
    logger.info("seeded users/departments/teachers/students", extra=created)
    return created


async def _seed_courses(session: AsyncSession) -> int:
    """Three courses per department, taught by the department's teacher, plus two class sessions per course."""
    departments = {d.code: d for d in (await session.execute(select(Department))).scalars()}
    teachers = {t.employee_id: t for t in (await session.execute(select(Teacher))).scalars()}
    existing_codes = await _existing(session, Course.course_code)
    created = 0
    for dept_index, (dept_code, _) in enumerate(DEPARTMENTS, start=1):
        teacher = teachers[f"EMP{dept_index:04d}"]
        for suffix, name, credits, semester in COURSES_BY_DEPT[dept_code]:
            code = f"{dept_code}{suffix}"
            if code in existing_codes:
                continue
            session.add(
                Course(
                    course_code=code,
                    course_name=name,
                    credits=credits,
                    department_id=departments[dept_code].id,
                    teacher_id=teacher.id,
                    semester=semester,
                )
            )
            created += 1
    await session.flush()

    courses = list((await session.execute(select(Course).order_by(Course.course_code))).scalars())
    existing_sessions = await _existing(session, ClassSession.course_id, ClassSession.name)
    sessions_created = 0
    for index, course in enumerate(courses):
        for slot, label in enumerate(("Lecture", "Lab")):
            name = f"{course.course_code} {label}"
            if (course.id, name) in existing_sessions:
                continue
            start_hour = 8 + (index + slot * 3) % 8
            session.add(
                ClassSession(
                    name=name,
                    course_id=course.id,
                    teacher_id=course.teacher_id,
                    room=ROOMS[(index + slot) % len(ROOMS)],
                    schedule_day=DAYS[(index + slot * 2) % len(DAYS)],
                    start_time=time(start_hour, 0),
                    end_time=time(start_hour + 1, 30),
                )
            )
            sessions_created += 1
    await session.commit()
    logger.info("seeded courses/classes", extra={"courses": created, "classSessions": sessions_created})
    return created


async def _seed_enrollments(session: AsyncSession) -> int:
    """Each student enrolls in three courses (semester = course semester); unique per student/course/semester."""
    students = list((await session.execute(select(Student).order_by(Student.student_id))).scalars())
    courses = list((await session.execute(select(Course).order_by(Course.course_code))).scalars())
    existing = await _existing(session, Enrollment.student_id, Enrollment.course_id, Enrollment.semester)
    created = 0
    for s_index, student in enumerate(students):
        for k, offset in enumerate((0, 5, 7)):
            course = courses[(s_index + offset) % len(courses)]
            if (student.id, course.id, course.semester) in existing:
                continue
            if s_index % 8 == 0 and k == 2:
                status = EnrollmentStatus.DROPPED
            elif s_index % 6 == 5 and k == 0:
                status = EnrollmentStatus.COMPLETED
            else:
                status = EnrollmentStatus.ACTIVE
            session.add(Enrollment(student_id=student.id, course_id=course.id, semester=course.semester, status=status))
            created += 1
    await session.commit()
    logger.info("seeded enrollments", extra={"enrollments": created})
    return created


async def _seed_assignments(session: AsyncSession) -> int:
    """Three assignments per course: CLOSED (past), PUBLISHED (future) and DRAFT / PUBLISHED-past alternating."""
    courses = list((await session.execute(select(Course).order_by(Course.course_code))).scalars())
    existing = await _existing(session, Assignment.course_id, Assignment.title)
    now = _utc_now()
    created = 0
    for index, course in enumerate(courses):
        if index % 2 == 0:
            third_status, third_due = AssignmentStatus.DRAFT, now + timedelta(days=21)
        else:
            third_status, third_due = AssignmentStatus.PUBLISHED, now - timedelta(days=3)
        specs = [
            ("Assignment 1 - Fundamentals", AssignmentStatus.CLOSED, now - timedelta(days=14), 100.0),
            ("Assignment 2 - Problem Set", AssignmentStatus.PUBLISHED, now + timedelta(days=5 + index), 50.0),
            ("Assignment 3 - Project", third_status, third_due, 100.0),
        ]
        for title, status, due, max_marks in specs:
            if (course.id, title) in existing:
                continue
            session.add(
                Assignment(
                    title=title,
                    description=f"{title} for {course.course_name}",
                    course_id=course.id,
                    teacher_id=course.teacher_id,
                    due_date=due,
                    max_marks=max_marks,
                    status=status,
                )
            )
            created += 1
    await session.commit()
    logger.info("seeded assignments", extra={"assignments": created})
    return created


async def _seed_attendance(session: AsyncSession) -> int:
    """Five past class days per non-dropped enrollment; skipped for student/course pairs already having rows."""
    teacher_user = {t.id: t.user_id for t in (await session.execute(select(Teacher))).scalars()}
    courses = {c.id: c for c in (await session.execute(select(Course))).scalars()}
    enrollments = (
        (
            await session.execute(
                select(Enrollment)
                .where(Enrollment.status != EnrollmentStatus.DROPPED)
                .order_by(Enrollment.student_id, Enrollment.course_id)
            )
        )
        .scalars()
        .all()
    )
    seeded_pairs = await _existing(session, Attendance.student_id, Attendance.course_id)
    today = date.today()
    created = 0
    for n, enrollment in enumerate(enrollments):
        if (enrollment.student_id, enrollment.course_id) in seeded_pairs:
            continue
        marker = teacher_user.get(courses[enrollment.course_id].teacher_id)
        for day in range(5):
            session.add(
                Attendance(
                    student_id=enrollment.student_id,
                    course_id=enrollment.course_id,
                    date=today - timedelta(days=day * 2 + 1),
                    status=ATTENDANCE_PATTERN[(n + day * 2) % len(ATTENDANCE_PATTERN)],
                    marked_by=marker,
                )
            )
            created += 1
    await session.commit()
    logger.info("seeded attendance", extra={"attendance": created})
    return created


async def _seed_grades(session: AsyncSession) -> int:
    """A grade for the CLOSED assignment of every course a student is (or was) enrolled in."""
    closed_rows = await session.execute(select(Assignment).where(Assignment.status == AssignmentStatus.CLOSED))
    closed = {a.course_id: a for a in closed_rows.scalars()}
    enrollments = (
        (
            await session.execute(
                select(Enrollment)
                .where(Enrollment.status != EnrollmentStatus.DROPPED)
                .order_by(Enrollment.student_id, Enrollment.course_id)
            )
        )
        .scalars()
        .all()
    )
    existing = await _existing(session, Grade.student_id, Grade.course_id, Grade.assignment_id)
    created = 0
    for n, enrollment in enumerate(enrollments):
        assignment = closed.get(enrollment.course_id)
        if assignment is None or (enrollment.student_id, enrollment.course_id, assignment.id) in existing:
            continue
        ratio = 0.42 + ((n * 7) % 57) / 100  # 0.42 .. 0.98 -> a spread of letter grades
        marks = round(assignment.max_marks * ratio, 1)
        session.add(
            Grade(
                student_id=enrollment.student_id,
                course_id=enrollment.course_id,
                assignment_id=assignment.id,
                marks=marks,
                max_marks=assignment.max_marks,
                grade=calculate_grade_letter(marks, assignment.max_marks),
            )
        )
        created += 1
    await session.commit()
    logger.info("seeded grades", extra={"grades": created})
    return created


async def _seed_notifications(session: AsyncSession) -> int:
    users = list((await session.execute(select(User).order_by(User.email))).scalars())
    existing = await _existing(session, Notification.user_id, Notification.title)
    templates = {
        UserRole.ADMIN: ADMIN_NOTIFICATIONS,
        UserRole.TEACHER: TEACHER_NOTIFICATIONS,
        UserRole.STUDENT: STUDENT_NOTIFICATIONS,
    }
    created = 0
    for user in users:
        for title, message, type_, is_read in templates[user.role]:
            if (user.id, title) in existing:
                continue
            session.add(Notification(user_id=user.id, title=title, message=message, type=type_, is_read=is_read))
            created += 1
    await session.commit()
    logger.info("seeded notifications", extra={"notifications": created})
    return created


async def seed(session: AsyncSession) -> dict[str, int]:
    """Run every seeding step in dependency order and return the resulting table row counts."""
    passwords = _PasswordCache()
    await _seed_people(session, passwords)
    await _seed_courses(session)
    await _seed_enrollments(session)
    await _seed_assignments(session)
    await _seed_attendance(session)
    await _seed_grades(session)
    await _seed_notifications(session)

    models = (
        User,
        Department,
        Teacher,
        Student,
        Course,
        ClassSession,
        Enrollment,
        Attendance,
        Grade,
        Assignment,
        Notification,
    )
    totals: dict[str, int] = {}
    for model in models:
        totals[model.__tablename__] = (await session.execute(select(func.count()).select_from(model))).scalar_one()
    return totals


async def main() -> None:
    configure_logging()
    try:
        async with SessionFactory() as session:
            totals = await seed(session)
        logger.info("seed complete", extra={"totals": totals})
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
