import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import AssignmentStatus


class Assignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assignments"
    __table_args__ = (CheckConstraint("max_marks > 0", name="max_marks_positive"),)

    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_marks: Mapped[float] = mapped_column(Float)
    status: Mapped[AssignmentStatus] = mapped_column(enum_column(AssignmentStatus), default=AssignmentStatus.DRAFT)
