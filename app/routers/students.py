import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AdminPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import StudentStatus
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.student import (
    StudentCreateRequest,
    StudentResponse,
    StudentStatusUpdateRequest,
    StudentUpdateRequest,
)
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["Students"])


def get_student_service(session: SessionDep) -> StudentService:
    return StudentService(session)


StudentServiceDep = Annotated[StudentService, Depends(get_student_service)]


@router.get(
    "",
    response_model=PagedApiResponse[StudentResponse],
    summary="List students (a STUDENT only sees their own record)",
)
async def list_students(
    principal: CurrentPrincipal,
    params: PageParamsDep,
    service: StudentServiceDep,
    department_id: Annotated[uuid.UUID | None, Query(alias="departmentId", description="Filter by department")] = None,
    semester: Annotated[int | None, Query(gt=0, description="Filter by semester")] = None,
    student_status: Annotated[StudentStatus | None, Query(alias="status", description="Filter by status")] = None,
) -> PagedApiResponse[StudentResponse]:
    page = await service.list(principal, params, department_id, semester, student_status)
    return paged_success(page.map(StudentResponse.from_entity), "Students retrieved successfully")


@router.get(
    "/{student_id}",
    response_model=ApiResponse[StudentResponse],
    summary="Get a student (a STUDENT only their own record)",
)
async def get_student(
    student_id: uuid.UUID, principal: CurrentPrincipal, service: StudentServiceDep
) -> ApiResponse[StudentResponse]:
    student = await service.get_for(principal, student_id)
    return success(StudentResponse.from_entity(student), "Student retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[StudentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a student with its user account (ADMIN)",
)
async def create_student(
    body: StudentCreateRequest, _: AdminPrincipal, service: StudentServiceDep
) -> ApiResponse[StudentResponse]:
    student = await service.create(body)
    return success(StudentResponse.from_entity(student), "Student created successfully")


@router.put("/{student_id}", response_model=ApiResponse[StudentResponse], summary="Update a student (ADMIN)")
async def update_student(
    student_id: uuid.UUID, body: StudentUpdateRequest, _: AdminPrincipal, service: StudentServiceDep
) -> ApiResponse[StudentResponse]:
    student = await service.update(student_id, body)
    return success(StudentResponse.from_entity(student), "Student updated successfully")


@router.patch(
    "/{student_id}/status", response_model=ApiResponse[StudentResponse], summary="Change a student's status (ADMIN)"
)
async def update_student_status(
    student_id: uuid.UUID, body: StudentStatusUpdateRequest, _: AdminPrincipal, service: StudentServiceDep
) -> ApiResponse[StudentResponse]:
    student = await service.update_status(student_id, body.status)
    return success(StudentResponse.from_entity(student), "Student status updated successfully")


@router.delete("/{student_id}", response_model=ApiResponse[None], summary="Delete a student and its user (ADMIN)")
async def delete_student(student_id: uuid.UUID, _: AdminPrincipal, service: StudentServiceDep) -> ApiResponse[None]:
    await service.delete(student_id)
    return success(None, "Student deleted successfully")
