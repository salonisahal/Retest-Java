import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import EmailStr, Field, StringConstraints

from app.models.enums import StudentStatus
from app.models.student import Student
from app.schemas.base import CamelModel

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
StudentCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class StudentCreateRequest(CamelModel):
    first_name: PersonName
    last_name: PersonName
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: Phone | None = None
    student_id: StudentCode
    department_id: uuid.UUID
    semester: int = Field(gt=0)
    status: StudentStatus = StudentStatus.ACTIVE


class StudentUpdateRequest(CamelModel):
    first_name: PersonName
    last_name: PersonName
    email: EmailStr
    phone: Phone | None = None
    student_id: StudentCode
    department_id: uuid.UUID
    semester: int = Field(gt=0)
    status: StudentStatus = StudentStatus.ACTIVE


class StudentStatusUpdateRequest(CamelModel):
    status: StudentStatus


class StudentResponse(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    student_id: str
    department_id: uuid.UUID
    semester: int
    status: StudentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, student: Student) -> Self:
        """Build the DTO from a student whose ``user`` relationship is loaded (it is selectin-loaded)."""
        user = student.user
        return cls(
            id=student.id,
            user_id=student.user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            student_id=student.student_id,
            department_id=student.department_id,
            semester=student.semester,
            status=student.status,
            created_at=student.created_at,
            updated_at=student.updated_at,
        )
