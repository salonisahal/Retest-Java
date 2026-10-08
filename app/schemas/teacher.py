import uuid
from datetime import datetime
from typing import Annotated, Self

from pydantic import EmailStr, Field, StringConstraints

from app.models.teacher import Teacher
from app.schemas.base import CamelModel

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
EmployeeId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Specialization = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
TeacherStatus = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=30)]


class TeacherCreateRequest(CamelModel):
    first_name: PersonName
    last_name: PersonName
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    phone: Phone | None = None
    employee_id: EmployeeId
    department_id: uuid.UUID
    specialization: Specialization
    status: TeacherStatus = "ACTIVE"


class TeacherUpdateRequest(CamelModel):
    first_name: PersonName
    last_name: PersonName
    email: EmailStr
    phone: Phone | None = None
    employee_id: EmployeeId
    department_id: uuid.UUID
    specialization: Specialization
    status: TeacherStatus = "ACTIVE"


class TeacherResponse(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    employee_id: str
    department_id: uuid.UUID
    specialization: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, teacher: Teacher) -> Self:
        """Build the DTO from a teacher whose ``user`` relationship is loaded (it is selectin-loaded)."""
        user = teacher.user
        return cls(
            id=teacher.id,
            user_id=teacher.user_id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            employee_id=teacher.employee_id,
            department_id=teacher.department_id,
            specialization=teacher.specialization,
            status=teacher.status,
            created_at=teacher.created_at,
            updated_at=teacher.updated_at,
        )
