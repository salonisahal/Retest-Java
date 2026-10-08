import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Grade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grades"
    __table_args__ = (
        CheckConstraint("max_marks > 0", name="max_marks_positive"),
        CheckConstraint("marks >= 0 AND marks <= max_marks", name="marks_in_range"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assignments.id", ondelete="SET NULL"))
    marks: Mapped[float] = mapped_column(Float)
    max_marks: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(2))
