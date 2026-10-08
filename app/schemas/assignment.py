"""Assignment request/response DTOs."""

import datetime as dt
import uuid

from pydantic import Field

from app.models.enums import AssignmentStatus
from app.schemas.base import CamelModel


class AssignmentCreate(CamelModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    due_date: dt.datetime
    max_marks: float = Field(gt=0)
    status: AssignmentStatus = AssignmentStatus.DRAFT


class AssignmentUpdate(CamelModel):
    """Partial update; omitted fields are unchanged (``description`` may be explicitly nulled)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    course_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    due_date: dt.datetime | None = None
    max_marks: float | None = Field(default=None, gt=0)
    status: AssignmentStatus | None = None


class AssignmentResponse(CamelModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    due_date: dt.datetime
    max_marks: float
    status: AssignmentStatus
    created_at: dt.datetime
    updated_at: dt.datetime
