"""Notification endpoints (every role, own notifications only)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import NotificationType
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.notification import NotificationResponse, ReadAllResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_notification_service(session: SessionDep) -> NotificationService:
    return NotificationService(session)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("", response_model=PagedApiResponse[NotificationResponse], summary="List own notifications")
async def list_notifications(
    principal: CurrentPrincipal,
    service: NotificationServiceDep,
    params: PageParamsDep,
    is_read: Annotated[bool | None, Query(alias="isRead", description="Filter by read state")] = None,
    type: Annotated[NotificationType | None, Query(description="Filter by notification type")] = None,
) -> PagedApiResponse[NotificationResponse]:
    page = await service.list_own(principal, params, is_read=is_read, type_=type)
    return paged_success(page.map(NotificationResponse.model_validate), "Notifications retrieved")


# Declared before "/{notification_id}/read" so the literal path is never captured as an id.
@router.patch("/read-all", response_model=ApiResponse[ReadAllResponse], summary="Mark all own notifications read")
async def mark_all_read(principal: CurrentPrincipal, service: NotificationServiceDep) -> ApiResponse[ReadAllResponse]:
    updated = await service.mark_all_read(principal)
    return success(ReadAllResponse(updated=updated), "All notifications marked as read")


@router.patch(
    "/{notification_id}/read", response_model=ApiResponse[NotificationResponse], summary="Mark a notification read"
)
async def mark_read(
    notification_id: uuid.UUID, principal: CurrentPrincipal, service: NotificationServiceDep
) -> ApiResponse[NotificationResponse]:
    notification = await service.mark_read(principal, notification_id)
    return success(NotificationResponse.model_validate(notification), "Notification marked as read")


@router.delete("/{notification_id}", response_model=ApiResponse[None], summary="Delete an own notification")
async def delete_notification(
    notification_id: uuid.UUID, principal: CurrentPrincipal, service: NotificationServiceDep
) -> ApiResponse[None]:
    await service.delete(principal, notification_id)
    return success(None, "Notification deleted")
