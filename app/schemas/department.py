import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.base import CamelModel

DepartmentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
DepartmentCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class DepartmentCreateRequest(CamelModel):
    name: DepartmentName
    code: DepartmentCode
    head_teacher_id: uuid.UUID | None = Field(default=None)


class DepartmentUpdateRequest(CamelModel):
    name: DepartmentName
    code: DepartmentCode
    head_teacher_id: uuid.UUID | None = Field(default=None)


class DepartmentResponse(CamelModel):
    id: uuid.UUID
    name: str
    code: str
    head_teacher_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
