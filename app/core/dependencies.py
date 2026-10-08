"""Shared FastAPI dependencies: DB session, authentication, role enforcement, access service."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.principal import Principal
from app.core.security import ACCESS_TOKEN, decode_token
from app.models.enums import UserRole, UserStatus
from app.repositories.course_repository import CourseRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.services.access_service import AccessService

# auto_error=False so a missing header yields our 401 envelope (not FastAPI's default 403).
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_principal(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    """Authenticate the request: valid access token for an existing, ACTIVE user, else 401."""
    if credentials is None:
        raise UnauthorizedError("Authentication required")
    payload = decode_token(credentials.credentials, ACCESS_TOKEN)
    user = await UserRepository(session).get(payload.user_id)
    if user is None or user.status is not UserStatus.ACTIVE:
        raise UnauthorizedError("Account not found or inactive")
    return Principal(user_id=user.id, email=user.email, role=user.role)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """Dependency factory: authenticated caller must hold one of ``roles`` (403 otherwise)."""

    async def checker(principal: CurrentPrincipal) -> Principal:
        if principal.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action")
        return principal

    return checker


AdminPrincipal = Annotated[Principal, Depends(require_roles(UserRole.ADMIN))]
AdminOrTeacherPrincipal = Annotated[Principal, Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER))]


def get_access_service(session: SessionDep) -> AccessService:
    return AccessService(TeacherRepository(session), StudentRepository(session), CourseRepository(session))


AccessServiceDep = Annotated[AccessService, Depends(get_access_service)]
