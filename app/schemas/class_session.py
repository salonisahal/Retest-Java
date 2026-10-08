import uuid
from datetime import datetime, time
from typing import Self

from pydantic import Field, model_validator

from app.models.enums import ScheduleDay
from app.schemas.base import CamelModel


class ClassRequest(CamelModel):
    """Body for POST and PUT /classes (times as HH:MM[:SS])."""

    name: str = Field(min_length=1, max_length=200)
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    room: str = Field(min_length=1, max_length=50)
    schedule_day: ScheduleDay
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _start_before_end(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("startTime must be before endTime")
        return self


class ClassResponse(CamelModel):
    id: uuid.UUID
    name: str
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    room: str
    schedule_day: ScheduleDay
    start_time: time
    end_time: time
    created_at: datetime
    updated_at: datetime
