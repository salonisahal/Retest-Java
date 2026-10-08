"""Attendance request/response DTOs."""

import datetime as dt
import uuid

from app.models.enums import AttendanceStatus
from app.schemas.base import CamelModel


class AttendanceCreate(CamelModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    date: dt.date
    status: AttendanceStatus


class AttendanceUpdate(CamelModel):
    """Only the status and/or date of a record can change (student/course are fixed)."""

    date: dt.date | None = None
    status: AttendanceStatus | None = None


class AttendanceResponse(CamelModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    date: dt.date
    status: AttendanceStatus
    marked_by: uuid.UUID | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
