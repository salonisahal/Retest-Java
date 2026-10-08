import uuid
from datetime import time

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import ScheduleDay


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("credits > 0", name="credits_positive"),
        CheckConstraint("semester > 0", name="semester_positive"),
    )

    course_code: Mapped[str] = mapped_column(String(30), unique=True)
    course_name: Mapped[str] = mapped_column(String(200))
    credits: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    semester: Mapped[int] = mapped_column(Integer)


class ClassSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A scheduled class session of a course (table ``classes``)."""

    __tablename__ = "classes"
    __table_args__ = (CheckConstraint("start_time < end_time", name="start_before_end"),)

    name: Mapped[str] = mapped_column(String(200))
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    room: Mapped[str] = mapped_column(String(50))
    schedule_day: Mapped[ScheduleDay] = mapped_column(enum_column(ScheduleDay))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
