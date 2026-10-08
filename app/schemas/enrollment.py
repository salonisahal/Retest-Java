import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import EnrollmentStatus
from app.schemas.base import CamelModel


class EnrollmentRequest(CamelModel):
    """Body for POST and PUT /enrollments."""

    student_id: uuid.UUID
    course_id: uuid.UUID
    semester: int = Field(gt=0)
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentResponse(CamelModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    semester: int
    status: EnrollmentStatus
    created_at: datetime
    updated_at: datetime
