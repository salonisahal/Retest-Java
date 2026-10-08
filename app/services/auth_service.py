"""Authentication use-cases: login, register, refresh-token rotation, logout."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    REFRESH_TOKEN,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole, UserStatus
from app.models.user import RefreshToken, User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

_INVALID_CREDENTIALS = "Invalid email or password"
_INVALID_REFRESH = "Invalid or expired refresh token"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._tokens = RefreshTokenRepository(session)

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self._users.get_by_email(data.email)
        # Same message for unknown email, wrong password and inactive account (no account enumeration).
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError(_INVALID_CREDENTIALS)
        if user.status is not UserStatus.ACTIVE:
            raise UnauthorizedError(_INVALID_CREDENTIALS)
        response = await self._issue_tokens(user)
        await self._session.commit()
        logger.info("User logged in: user_id=%s", user.id)
        return response

    async def register(self, data: RegisterRequest) -> UserResponse:
        if await self._users.email_taken(data.email):
            raise ConflictError("A user with this email already exists")
        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password_hash=hash_password(data.password),
            phone=data.phone,
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        await self._users.add(user)
        await self._session.commit()
        logger.info("User registered: user_id=%s", user.id)
        return UserResponse.model_validate(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, REFRESH_TOKEN)
        stored = await self._tokens.get_by_hash(hash_token(refresh_token))
        if (
            stored is None
            or stored.user_id != payload.user_id
            or stored.revoked
            or self._as_utc(stored.expires_at) <= datetime.now(UTC)
        ):
            raise UnauthorizedError(_INVALID_REFRESH)
        user = await self._users.get(stored.user_id)
        if user is None or user.status is not UserStatus.ACTIVE:
            raise UnauthorizedError(_INVALID_REFRESH)
        # Rotation: the old token is single-use. The conditional UPDATE makes concurrent reuse fail.
        if not await self._tokens.revoke_if_active(stored.id):
            raise UnauthorizedError(_INVALID_REFRESH)
        response = await self._issue_tokens(user)
        await self._session.commit()
        return response

    async def logout(self, user_id: uuid.UUID, refresh_token: str) -> None:
        """Revoke the caller's own refresh token. Unknown tokens and other users' tokens are ignored (idempotent)."""
        stored = await self._tokens.get_by_hash(hash_token(refresh_token))
        if stored is not None and stored.user_id == user_id and not stored.revoked:
            await self._tokens.revoke_if_active(stored.id)
            await self._session.commit()
            logger.info("User logged out: user_id=%s", user_id)

    async def get_me(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._users.get(user_id)
        if user is None:
            raise UnauthorizedError("Account not found or inactive")
        return UserResponse.model_validate(user)

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(user.id, user.email, user.role.value)
        refresh = create_refresh_token(user.id, user.email, user.role.value)
        await self._tokens.add(
            RefreshToken(user_id=user.id, token_hash=hash_token(refresh.token), expires_at=refresh.expires_at)
        )
        return TokenResponse(
            access_token=access.token,
            refresh_token=refresh.token,
            token_type="Bearer",
            expires_in=get_settings().access_token_expire_seconds,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
