import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AdminOrTeacherPrincipal, AdminPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.teacher import TeacherCreateRequest, TeacherResponse, TeacherUpdateRequest
from app.services.teacher_service import TeacherService

router = APIRouter(prefix="/teachers", tags=["Teachers"])


def get_teacher_service(session: SessionDep) -> TeacherService:
    return TeacherService(session)


TeacherServiceDep = Annotated[TeacherService, Depends(get_teacher_service)]


@router.get("", response_model=PagedApiResponse[TeacherResponse], summary="List teachers (ADMIN, TEACHER)")
async def list_teachers(
    _: AdminOrTeacherPrincipal,
    params: PageParamsDep,
    service: TeacherServiceDep,
    department_id: Annotated[uuid.UUID | None, Query(alias="departmentId", description="Filter by department")] = None,
) -> PagedApiResponse[TeacherResponse]:
    page = await service.list(params, department_id)
    return paged_success(page.map(TeacherResponse.from_entity), "Teachers retrieved successfully")


@router.get("/{teacher_id}", response_model=ApiResponse[TeacherResponse], summary="Get a teacher (ADMIN, TEACHER)")
async def get_teacher(
    teacher_id: uuid.UUID, _: AdminOrTeacherPrincipal, service: TeacherServiceDep
) -> ApiResponse[TeacherResponse]:
    teacher = await service.get(teacher_id)
    return success(TeacherResponse.from_entity(teacher), "Teacher retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[TeacherResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a teacher with its user account (ADMIN)",
)
async def create_teacher(
    body: TeacherCreateRequest, _: AdminPrincipal, service: TeacherServiceDep
) -> ApiResponse[TeacherResponse]:
    teacher = await service.create(body)
    return success(TeacherResponse.from_entity(teacher), "Teacher created successfully")


@router.put("/{teacher_id}", response_model=ApiResponse[TeacherResponse], summary="Update a teacher (ADMIN)")
async def update_teacher(
    teacher_id: uuid.UUID, body: TeacherUpdateRequest, _: AdminPrincipal, service: TeacherServiceDep
) -> ApiResponse[TeacherResponse]:
    teacher = await service.update(teacher_id, body)
    return success(TeacherResponse.from_entity(teacher), "Teacher updated successfully")


@router.delete("/{teacher_id}", response_model=ApiResponse[None], summary="Delete a teacher and its user (ADMIN)")
async def delete_teacher(teacher_id: uuid.UUID, _: AdminPrincipal, service: TeacherServiceDep) -> ApiResponse[None]:
    await service.delete(teacher_id)
    return success(None, "Teacher deleted successfully")
