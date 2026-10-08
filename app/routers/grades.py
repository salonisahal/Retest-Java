"""Grade endpoints (mounted at /api/v1/grades)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import AccessServiceDep, AdminOrTeacherPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.grade import GradeCreate, GradeResponse, GradeUpdate
from app.services.grade_service import GradeService

router = APIRouter(prefix="/grades", tags=["Grades"])


def get_grade_service(session: SessionDep, access: AccessServiceDep) -> GradeService:
    return GradeService(session, access)


GradeServiceDep = Annotated[GradeService, Depends(get_grade_service)]


@router.get("", response_model=PagedApiResponse[GradeResponse], summary="List grades")
async def list_grades(
    principal: CurrentPrincipal,
    service: GradeServiceDep,
    params: PageParamsDep,
    student_id: Annotated[uuid.UUID | None, Query(alias="studentId", description="Filter by student id")] = None,
    course_id: Annotated[uuid.UUID | None, Query(alias="courseId", description="Filter by course id")] = None,
    assignment_id: Annotated[
        uuid.UUID | None, Query(alias="assignmentId", description="Filter by assignment id")
    ] = None,
) -> PagedApiResponse[GradeResponse]:
    page = await service.list_grades(
        principal, params, student_id=student_id, course_id=course_id, assignment_id=assignment_id
    )
    return paged_success(page.map(GradeResponse.model_validate), "Grades retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[GradeResponse],
    status_code=201,
    summary="Record a grade (ADMIN or the course's TEACHER); the letter is computed by the server",
)
async def create_grade(
    body: GradeCreate, principal: AdminOrTeacherPrincipal, service: GradeServiceDep
) -> ApiResponse[GradeResponse]:
    grade = await service.create(principal, body)
    return success(GradeResponse.model_validate(grade), "Grade recorded successfully")


@router.get("/{grade_id}", response_model=ApiResponse[GradeResponse], summary="Get grade")
async def get_grade(
    grade_id: uuid.UUID, principal: CurrentPrincipal, service: GradeServiceDep
) -> ApiResponse[GradeResponse]:
    grade = await service.get_grade(principal, grade_id)
    return success(GradeResponse.model_validate(grade), "Grade retrieved successfully")


@router.put("/{grade_id}", response_model=ApiResponse[GradeResponse], summary="Update grade (letter recomputed)")
async def update_grade(
    grade_id: uuid.UUID, body: GradeUpdate, principal: AdminOrTeacherPrincipal, service: GradeServiceDep
) -> ApiResponse[GradeResponse]:
    grade = await service.update(principal, grade_id, body)
    return success(GradeResponse.model_validate(grade), "Grade updated successfully")


@router.delete("/{grade_id}", response_model=ApiResponse[None], summary="Delete grade")
async def delete_grade(
    grade_id: uuid.UUID, principal: AdminOrTeacherPrincipal, service: GradeServiceDep
) -> ApiResponse[None]:
    await service.delete(principal, grade_id)
    return success(None, "Grade deleted successfully")
