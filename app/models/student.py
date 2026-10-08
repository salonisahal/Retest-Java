import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import StudentStatus
from app.models.user import User


class Student(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("semester > 0", name="semester_positive"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)
    semester: Mapped[int] = mapped_column(Integer)
    status: Mapped[StudentStatus] = mapped_column(enum_column(StudentStatus), default=StudentStatus.ACTIVE)

    user: Mapped[User] = relationship(lazy="selectin")
