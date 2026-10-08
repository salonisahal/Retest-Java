"""Notification DTOs."""

import uuid
from datetime import datetime

from app.models.enums import NotificationType
from app.schemas.base import CamelModel


class NotificationResponse(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime
    updated_at: datetime


class ReadAllResponse(CamelModel):
    updated: int
