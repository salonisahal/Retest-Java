"""Notification use-cases: a user's own inbox plus a helper other services can call to notify users."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notifications = NotificationRepository(session)

    async def create_for_user(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
    ) -> Notification:
        """Stage a notification for ``user_id`` and flush it.

        This does NOT commit: the caller owns the transaction and must commit (so the notification
        is persisted atomically with the business change that triggered it).
        """
        notification = Notification(user_id=user_id, title=title, message=message, type=type, is_read=False)
        return await self._notifications.add(notification)

    async def list_own(
        self,
        principal: Principal,
        params: PageParams,
        *,
        is_read: bool | None,
        type_: NotificationType | None,
    ) -> Page[Notification]:
        return await self._notifications.list_for_user(principal.user_id, params, is_read=is_read, type_=type_)

    async def mark_all_read(self, principal: Principal) -> int:
        updated = await self._notifications.mark_all_read(principal.user_id)
        await self._session.commit()
        logger.info("notifications marked read", extra={"userId": str(principal.user_id), "updated": updated})
        return updated

    async def mark_read(self, principal: Principal, notification_id: uuid.UUID) -> Notification:
        notification = await self._get_own(principal, notification_id)
        if not notification.is_read:
            notification.is_read = True
            await self._session.commit()
        return notification

    async def delete(self, principal: Principal, notification_id: uuid.UUID) -> None:
        notification = await self._get_own(principal, notification_id)
        await self._notifications.delete(notification)
        await self._session.commit()

    async def _get_own(self, principal: Principal, notification_id: uuid.UUID) -> Notification:
        """Someone else's notification is indistinguishable from a missing one (404)."""
        notification = await self._notifications.get_for_user(notification_id, principal.user_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        return notification
