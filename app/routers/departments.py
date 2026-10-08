import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.dependencies import AdminPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.department import DepartmentCreateRequest, DepartmentResponse, DepartmentUpdateRequest
from app.services.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


def get_department_service(session: SessionDep) -> DepartmentService:
    return DepartmentService(session)


DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]


@router.get("", response_model=PagedApiResponse[DepartmentResponse], summary="List departments")
async def list_departments(
    _: CurrentPrincipal, params: PageParamsDep, service: DepartmentServiceDep
) -> PagedApiResponse[DepartmentResponse]:
    page = await service.list(params)
    return paged_success(page.map(DepartmentResponse.model_validate), "Departments retrieved successfully")


@router.get("/{department_id}", response_model=ApiResponse[DepartmentResponse], summary="Get a department")
async def get_department(
    department_id: uuid.UUID, _: CurrentPrincipal, service: DepartmentServiceDep
) -> ApiResponse[DepartmentResponse]:
    department = await service.get(department_id)
    return success(DepartmentResponse.model_validate(department), "Department retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[DepartmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a department (ADMIN)",
)
async def create_department(
    body: DepartmentCreateRequest, _: AdminPrincipal, service: DepartmentServiceDep
) -> ApiResponse[DepartmentResponse]:
    department = await service.create(body)
    return success(DepartmentResponse.model_validate(department), "Department created successfully")


@router.put("/{department_id}", response_model=ApiResponse[DepartmentResponse], summary="Update a department (ADMIN)")
async def update_department(
    department_id: uuid.UUID, body: DepartmentUpdateRequest, _: AdminPrincipal, service: DepartmentServiceDep
) -> ApiResponse[DepartmentResponse]:
    department = await service.update(department_id, body)
    return success(DepartmentResponse.model_validate(department), "Department updated successfully")


@router.delete("/{department_id}", response_model=ApiResponse[None], summary="Delete a department (ADMIN)")
async def delete_department(
    department_id: uuid.UUID, _: AdminPrincipal, service: DepartmentServiceDep
) -> ApiResponse[None]:
    await service.delete(department_id)
    return success(None, "Department deleted successfully")
