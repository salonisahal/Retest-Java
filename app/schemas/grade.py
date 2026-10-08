"""Grade request/response DTOs. The letter ``grade`` is computed server-side and never accepted from clients."""

import datetime as dt
import uuid

from pydantic import Field, ValidationInfo, field_validator

from app.schemas.base import CamelModel

_MARKS_EXCEED_MESSAGE = "marks must not exceed maxMarks"


class GradeCreate(CamelModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    assignment_id: uuid.UUID | None = None
    # maxMarks is declared before marks so the marks validator can compare against it.
    max_marks: float = Field(gt=0)
    marks: float = Field(ge=0)

    @field_validator("marks")
    @classmethod
    def marks_not_above_max(cls, value: float, info: ValidationInfo) -> float:
        max_marks = info.data.get("max_marks")
        if max_marks is not None and value > max_marks:
            raise ValueError(_MARKS_EXCEED_MESSAGE)
        return value


class GradeUpdate(CamelModel):
    """Partial update; the service re-checks marks <= maxMarks against the merged values."""

    assignment_id: uuid.UUID | None = None
    max_marks: float | None = Field(default=None, gt=0)
    marks: float | None = Field(default=None, ge=0)

    @field_validator("marks")
    @classmethod
    def marks_not_above_max(cls, value: float | None, info: ValidationInfo) -> float | None:
        max_marks = info.data.get("max_marks")
        if value is not None and max_marks is not None and value > max_marks:
            raise ValueError(_MARKS_EXCEED_MESSAGE)
        return value


class GradeResponse(CamelModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    assignment_id: uuid.UUID | None = None
    marks: float
    max_marks: float
    grade: str
    created_at: dt.datetime
    updated_at: dt.datetime
