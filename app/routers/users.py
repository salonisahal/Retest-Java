"""User administration endpoints (ADMIN only)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AdminPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import UserRole, UserStatus
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.user import UserCreateRequest, UserResponse, UserStatusUpdateRequest, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "",
    response_model=PagedApiResponse[UserResponse],
    summary="List users (paged, searchable, filterable)",
)
async def list_users(
    _: AdminPrincipal,
    service: UserServiceDep,
    params: PageParamsDep,
    role: Annotated[UserRole | None, Query(description="Filter by role")] = None,
    status: Annotated[UserStatus | None, Query(description="Filter by status")] = None,
) -> PagedApiResponse[UserResponse]:
    page = await service.list_users(params, role=role, status=status)
    return paged_success(page, "Users retrieved successfully")


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Get a user by id",
    responses={404: {"description": "User not found"}},
)
async def get_user(user_id: uuid.UUID, _: AdminPrincipal, service: UserServiceDep) -> ApiResponse[UserResponse]:
    return success(await service.get_user(user_id), "User retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a user with any role",
    responses={409: {"description": "Email already exists"}},
)
async def create_user(body: UserCreateRequest, _: AdminPrincipal, service: UserServiceDep) -> ApiResponse[UserResponse]:
    return success(await service.create_user(body), "User created successfully")


@router.put(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Update a user (full replace; optional password reset)",
    responses={404: {"description": "User not found"}, 409: {"description": "Email already exists"}},
)
async def update_user(
    user_id: uuid.UUID, body: UserUpdateRequest, _: AdminPrincipal, service: UserServiceDep
) -> ApiResponse[UserResponse]:
    return success(await service.update_user(user_id, body), "User updated successfully")


@router.patch(
    "/{user_id}/status",
    response_model=ApiResponse[UserResponse],
    summary="Activate or deactivate a user",
    responses={404: {"description": "User not found"}},
)
async def update_user_status(
    user_id: uuid.UUID, body: UserStatusUpdateRequest, _: AdminPrincipal, service: UserServiceDep
) -> ApiResponse[UserResponse]:
    return success(await service.update_status(user_id, body.status), "User status updated successfully")


@router.delete(
    "/{user_id}",
    response_model=ApiResponse[None],
    summary="Delete a user",
    responses={400: {"description": "Cannot delete yourself"}, 404: {"description": "User not found"}},
)
async def delete_user(user_id: uuid.UUID, principal: AdminPrincipal, service: UserServiceDep) -> ApiResponse[None]:
    await service.delete_user(user_id, principal.user_id)
    return success(None, "User deleted successfully")
