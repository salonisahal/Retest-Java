"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentPrincipal, SessionDep
from app.core.pagination import success
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from app.schemas.base import ApiResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Log in with email and password",
    responses={401: {"description": "Invalid credentials or inactive account"}},
)
async def login(body: LoginRequest, service: AuthServiceDep) -> ApiResponse[TokenResponse]:
    return success(await service.login(body), "Login successful")


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new STUDENT account",
    responses={409: {"description": "Email already registered"}},
)
async def register(body: RegisterRequest, service: AuthServiceDep) -> ApiResponse[UserResponse]:
    return success(await service.register(body), "User registered successfully")


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Exchange a refresh token for a new access/refresh token pair",
    responses={401: {"description": "Invalid, expired or revoked refresh token"}},
)
async def refresh(body: RefreshTokenRequest, service: AuthServiceDep) -> ApiResponse[TokenResponse]:
    return success(await service.refresh(body.refresh_token), "Token refreshed successfully")


@router.post(
    "/logout",
    response_model=ApiResponse[None],
    summary="Log out (revoke the given refresh token)",
)
async def logout(body: LogoutRequest, principal: CurrentPrincipal, service: AuthServiceDep) -> ApiResponse[None]:
    await service.logout(principal.user_id, body.refresh_token)
    return success(None, "Logged out successfully")


@router.get("/me", response_model=ApiResponse[UserResponse], summary="Get the authenticated user")
async def me(principal: CurrentPrincipal, service: AuthServiceDep) -> ApiResponse[UserResponse]:
    return success(await service.get_me(principal.user_id), "Current user retrieved successfully")
