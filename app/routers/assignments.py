"""Assignment endpoints (mounted at /api/v1/assignments)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import AccessServiceDep, AdminOrTeacherPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import AssignmentStatus
from app.schemas.assignment import AssignmentCreate, AssignmentResponse, AssignmentUpdate
from app.schemas.base import ApiResponse, PagedApiResponse
from app.services.assignment_service import AssignmentService

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def get_assignment_service(session: SessionDep, access: AccessServiceDep) -> AssignmentService:
    return AssignmentService(session, access)


AssignmentServiceDep = Annotated[AssignmentService, Depends(get_assignment_service)]


@router.get("", response_model=PagedApiResponse[AssignmentResponse], summary="List assignments")
async def list_assignments(
    principal: CurrentPrincipal,
    service: AssignmentServiceDep,
    params: PageParamsDep,
    course_id: Annotated[uuid.UUID | None, Query(alias="courseId", description="Filter by course id")] = None,
    status: Annotated[AssignmentStatus | None, Query(description="Filter by status")] = None,
) -> PagedApiResponse[AssignmentResponse]:
    page = await service.list_assignments(principal, params, course_id=course_id, status=status, search=params.search)
    return paged_success(page.map(AssignmentResponse.model_validate), "Assignments retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[AssignmentResponse],
    status_code=201,
    summary="Create assignment (ADMIN or the course's TEACHER)",
)
async def create_assignment(
    body: AssignmentCreate, principal: AdminOrTeacherPrincipal, service: AssignmentServiceDep
) -> ApiResponse[AssignmentResponse]:
    assignment = await service.create(principal, body)
    return success(AssignmentResponse.model_validate(assignment), "Assignment created successfully")


@router.get("/{assignment_id}", response_model=ApiResponse[AssignmentResponse], summary="Get assignment")
async def get_assignment(
    assignment_id: uuid.UUID, principal: CurrentPrincipal, service: AssignmentServiceDep
) -> ApiResponse[AssignmentResponse]:
    assignment = await service.get_assignment(principal, assignment_id)
    return success(AssignmentResponse.model_validate(assignment), "Assignment retrieved successfully")


@router.put("/{assignment_id}", response_model=ApiResponse[AssignmentResponse], summary="Update assignment")
async def update_assignment(
    assignment_id: uuid.UUID,
    body: AssignmentUpdate,
    principal: AdminOrTeacherPrincipal,
    service: AssignmentServiceDep,
) -> ApiResponse[AssignmentResponse]:
    assignment = await service.update(principal, assignment_id, body)
    return success(AssignmentResponse.model_validate(assignment), "Assignment updated successfully")


@router.delete("/{assignment_id}", response_model=ApiResponse[None], summary="Delete assignment")
async def delete_assignment(
    assignment_id: uuid.UUID, principal: AdminOrTeacherPrincipal, service: AssignmentServiceDep
) -> ApiResponse[None]:
    await service.delete(principal, assignment_id)
    return success(None, "Assignment deleted successfully")
