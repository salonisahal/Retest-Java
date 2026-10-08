import uuid

from sqlalchemy import func, select, update

from app.core.pagination import Page, PageParams
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.repositories.base import BaseRepository

_SORTABLE = {
    "id": Notification.id,
    "title": Notification.title,
    "type": Notification.type,
    "isRead": Notification.is_read,
    "createdAt": Notification.created_at,
}


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        params: PageParams,
        *,
        is_read: bool | None = None,
        type_: NotificationType | None = None,
    ) -> Page[Notification]:
        """Page of the user's own notifications (newest first by default)."""
        stmt = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read.is_(is_read))
        if type_ is not None:
            stmt = stmt.where(Notification.type == type_)
        clause = self.search_clause(params.search, [Notification.title, Notification.message])
        if clause is not None:
            stmt = stmt.where(clause)
        return await self.paginate(
            stmt,
            params,
            sortable=_SORTABLE,
            default_sort=[Notification.created_at.desc(), Notification.id.desc()],
        )

    async def get_for_user(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        """The notification only when it belongs to ``user_id``."""
        return await self.get_by(id=notification_id, user_id=user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Bulk-mark the user's unread notifications as read; returns the number updated (no commit)."""
        result = await self._session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True, updated_at=func.now())
            .execution_options(synchronize_session=False)
        )
        return result.rowcount or 0

    async def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return (await self._session.execute(stmt)).scalar_one()
