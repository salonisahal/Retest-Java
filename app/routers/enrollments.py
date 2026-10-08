import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AccessServiceDep, AdminOrTeacherPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import EnrollmentStatus
from app.repositories.course_repository import CourseRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.enrollment import EnrollmentRequest, EnrollmentResponse
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


def get_enrollment_service(session: SessionDep, access: AccessServiceDep) -> EnrollmentService:
    return EnrollmentService(
        session, EnrollmentRepository(session), CourseRepository(session), StudentRepository(session), access
    )


EnrollmentServiceDep = Annotated[EnrollmentService, Depends(get_enrollment_service)]


@router.get("", response_model=PagedApiResponse[EnrollmentResponse], summary="List enrollments (role-scoped)")
async def list_enrollments(
    principal: CurrentPrincipal,
    service: EnrollmentServiceDep,
    params: PageParamsDep,
    student_id: Annotated[uuid.UUID | None, Query(alias="studentId")] = None,
    course_id: Annotated[uuid.UUID | None, Query(alias="courseId")] = None,
    semester: Annotated[int | None, Query(gt=0)] = None,
    status_: Annotated[EnrollmentStatus | None, Query(alias="status")] = None,
):
    page = await service.list_enrollments(principal, params, student_id, course_id, semester, status_)
    return paged_success(page.map(EnrollmentResponse.model_validate), "Enrollments retrieved successfully")


@router.get("/{enrollment_id}", response_model=ApiResponse[EnrollmentResponse], summary="Get an enrollment")
async def get_enrollment(enrollment_id: uuid.UUID, principal: CurrentPrincipal, service: EnrollmentServiceDep):
    enrollment = await service.get_enrollment(principal, enrollment_id)
    return success(EnrollmentResponse.model_validate(enrollment), "Enrollment retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[EnrollmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an enrollment (ADMIN, course teacher, or student self-enrolment)",
)
async def create_enrollment(request: EnrollmentRequest, principal: CurrentPrincipal, service: EnrollmentServiceDep):
    enrollment = await service.create_enrollment(principal, request)
    return success(EnrollmentResponse.model_validate(enrollment), "Enrollment created successfully")


@router.put(
    "/{enrollment_id}",
    response_model=ApiResponse[EnrollmentResponse],
    summary="Update an enrollment (ADMIN/course teacher)",
)
async def update_enrollment(
    enrollment_id: uuid.UUID,
    request: EnrollmentRequest,
    principal: AdminOrTeacherPrincipal,
    service: EnrollmentServiceDep,
):
    enrollment = await service.update_enrollment(principal, enrollment_id, request)
    return success(EnrollmentResponse.model_validate(enrollment), "Enrollment updated successfully")


@router.delete(
    "/{enrollment_id}",
    response_model=ApiResponse[None],
    summary="Delete an enrollment (ADMIN/course teacher)",
)
async def delete_enrollment(
    enrollment_id: uuid.UUID, principal: AdminOrTeacherPrincipal, service: EnrollmentServiceDep
):
    await service.delete_enrollment(principal, enrollment_id)
    return success(None, "Enrollment deleted successfully")
