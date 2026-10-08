"""Admin user management use-cases."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.security import hash_password
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest

logger = logging.getLogger(__name__)

_DUPLICATE_EMAIL = "A user with this email already exists"


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._tokens = RefreshTokenRepository(session)

    async def list_users(
        self, params: PageParams, role: UserRole | None = None, status: UserStatus | None = None
    ) -> Page[UserResponse]:
        page = await self._users.search(params, role=role, status=status)
        return page.map(UserResponse.model_validate)

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        return UserResponse.model_validate(await self._get_or_404(user_id))

    async def create_user(self, data: UserCreateRequest) -> UserResponse:
        if await self._users.email_taken(data.email):
            raise ConflictError(_DUPLICATE_EMAIL)
        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash=hash_password(data.password),
            phone=data.phone,
            role=data.role,
            status=data.status,
        )
        await self._users.add(user)
        await self._session.commit()
        logger.info("User created: user_id=%s role=%s", user.id, user.role)
        return UserResponse.model_validate(user)

    async def update_user(self, user_id: uuid.UUID, data: UserUpdateRequest) -> UserResponse:
        user = await self._get_or_404(user_id)
        if await self._users.email_taken(data.email, exclude_id=user.id):
            raise ConflictError(_DUPLICATE_EMAIL)
        user.first_name = data.first_name
        user.last_name = data.last_name
        user.email = data.email
        user.phone = data.phone
        user.role = data.role
        user.status = data.status
        if data.password:
            user.password_hash = hash_password(data.password)
        # Credentials changed or account disabled: existing sessions must not outlive that.
        if data.password or data.status is not UserStatus.ACTIVE:
            await self._tokens.revoke_all_for_user(user.id)
        await self._users.flush()
        await self._session.commit()
        logger.info("User updated: user_id=%s", user.id)
        return UserResponse.model_validate(user)

    async def update_status(self, user_id: uuid.UUID, status: UserStatus) -> UserResponse:
        user = await self._get_or_404(user_id)
        user.status = status
        if status is not UserStatus.ACTIVE:
            await self._tokens.revoke_all_for_user(user.id)
        await self._users.flush()
        await self._session.commit()
        logger.info("User status changed: user_id=%s status=%s", user.id, status)
        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: uuid.UUID, current_user_id: uuid.UUID) -> None:
        user = await self._get_or_404(user_id)
        if user.id == current_user_id:
            raise BadRequestError("You cannot delete your own account")
        await self._users.delete(user)
        await self._session.commit()
        logger.info("User deleted: user_id=%s", user_id)

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user
