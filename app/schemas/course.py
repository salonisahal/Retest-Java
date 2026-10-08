import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class CourseRequest(CamelModel):
    """Body for POST and PUT /courses."""

    course_code: str = Field(min_length=1, max_length=30)
    course_name: str = Field(min_length=1, max_length=200)
    credits: int = Field(gt=0)
    department_id: uuid.UUID
    teacher_id: uuid.UUID
    semester: int = Field(gt=0)


class CourseResponse(CamelModel):
    id: uuid.UUID
    course_code: str
    course_name: str
    credits: int
    department_id: uuid.UUID
    teacher_id: uuid.UUID
    semester: int
    created_at: datetime
    updated_at: datetime
