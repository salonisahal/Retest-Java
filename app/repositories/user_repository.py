import uuid

from sqlalchemy import func, select

from app.core.pagination import Page, PageParams
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.base import BaseRepository

USER_SORTABLE = {
    "id": User.id,
    "firstName": User.first_name,
    "lastName": User.last_name,
    "email": User.email,
    "role": User.role,
    "status": User.status,
    "createdAt": User.created_at,
}


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email)

    async def email_taken(self, email: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        """Case-insensitive duplicate check, optionally ignoring one user (for updates)."""
        stmt = select(func.count()).select_from(User).where(func.lower(User.email) == email.lower())
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return (await self._session.execute(stmt)).scalar_one() > 0

    async def search(
        self,
        params: PageParams,
        *,
        role: UserRole | None = None,
        status: UserStatus | None = None,
    ) -> Page[User]:
        stmt = select(User)
        clause = self.search_clause(params.search, [User.first_name, User.last_name, User.email])
        if clause is not None:
            stmt = stmt.where(clause)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if status is not None:
            stmt = stmt.where(User.status == status)
        return await self.paginate(
            stmt, params, sortable=USER_SORTABLE, default_sort=[User.created_at.desc(), User.id.asc()]
        )
