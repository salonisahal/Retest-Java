"""Attendance endpoints. Full paths are declared here (no router prefix) because they span /attendance,
/students/{id}/attendance and /courses/{id}/attendance."""

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import AccessServiceDep, AdminOrTeacherPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import AttendanceStatus
from app.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from app.schemas.base import ApiResponse, PagedApiResponse
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendance"])


def get_attendance_service(session: SessionDep, access: AccessServiceDep) -> AttendanceService:
    return AttendanceService(session, access)


AttendanceServiceDep = Annotated[AttendanceService, Depends(get_attendance_service)]

StudentIdQuery = Annotated[uuid.UUID | None, Query(alias="studentId", description="Filter by student id")]
CourseIdQuery = Annotated[uuid.UUID | None, Query(alias="courseId", description="Filter by course id")]
StatusQuery = Annotated[AttendanceStatus | None, Query(description="Filter by attendance status")]
DateFromQuery = Annotated[dt.date | None, Query(alias="dateFrom", description="Earliest date (inclusive)")]
DateToQuery = Annotated[dt.date | None, Query(alias="dateTo", description="Latest date (inclusive)")]


@router.get("/attendance", response_model=PagedApiResponse[AttendanceResponse], summary="List attendance records")
async def list_attendance(
    principal: CurrentPrincipal,
    service: AttendanceServiceDep,
    params: PageParamsDep,
    student_id: StudentIdQuery = None,
    course_id: CourseIdQuery = None,
    status: StatusQuery = None,
    date_from: DateFromQuery = None,
    date_to: DateToQuery = None,
) -> PagedApiResponse[AttendanceResponse]:
    page = await service.list_attendance(
        principal,
        params,
        student_id=student_id,
        course_id=course_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return paged_success(page.map(AttendanceResponse.model_validate), "Attendance retrieved successfully")


@router.post(
    "/attendance",
    response_model=ApiResponse[AttendanceResponse],
    status_code=201,
    summary="Mark attendance (ADMIN or the course's TEACHER)",
)
async def create_attendance(
    body: AttendanceCreate, principal: AdminOrTeacherPrincipal, service: AttendanceServiceDep
) -> ApiResponse[AttendanceResponse]:
    record = await service.create(principal, body)
    return success(AttendanceResponse.model_validate(record), "Attendance marked successfully")


@router.get(
    "/students/{student_id}/attendance",
    response_model=PagedApiResponse[AttendanceResponse],
    summary="List attendance of one student",
)
async def list_student_attendance(
    student_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: AttendanceServiceDep,
    params: PageParamsDep,
    course_id: CourseIdQuery = None,
    status: StatusQuery = None,
    date_from: DateFromQuery = None,
    date_to: DateToQuery = None,
) -> PagedApiResponse[AttendanceResponse]:
    page = await service.list_for_student(
        principal, student_id, params, course_id=course_id, status=status, date_from=date_from, date_to=date_to
    )
    return paged_success(page.map(AttendanceResponse.model_validate), "Attendance retrieved successfully")


@router.get(
    "/courses/{course_id}/attendance",
    response_model=PagedApiResponse[AttendanceResponse],
    summary="List attendance of one course (ADMIN or the course's TEACHER)",
)
async def list_course_attendance(
    course_id: uuid.UUID,
    principal: CurrentPrincipal,
    service: AttendanceServiceDep,
    params: PageParamsDep,
    student_id: StudentIdQuery = None,
    status: StatusQuery = None,
    date_from: DateFromQuery = None,
    date_to: DateToQuery = None,
) -> PagedApiResponse[AttendanceResponse]:
    page = await service.list_for_course(
        principal, course_id, params, student_id=student_id, status=status, date_from=date_from, date_to=date_to
    )
    return paged_success(page.map(AttendanceResponse.model_validate), "Attendance retrieved successfully")


@router.get("/attendance/{attendance_id}", response_model=ApiResponse[AttendanceResponse], summary="Get attendance")
async def get_attendance(
    attendance_id: uuid.UUID, principal: CurrentPrincipal, service: AttendanceServiceDep
) -> ApiResponse[AttendanceResponse]:
    record = await service.get_attendance(principal, attendance_id)
    return success(AttendanceResponse.model_validate(record), "Attendance retrieved successfully")


@router.put(
    "/attendance/{attendance_id}",
    response_model=ApiResponse[AttendanceResponse],
    summary="Update attendance status/date (ADMIN or the course's TEACHER)",
)
async def update_attendance(
    attendance_id: uuid.UUID,
    body: AttendanceUpdate,
    principal: AdminOrTeacherPrincipal,
    service: AttendanceServiceDep,
) -> ApiResponse[AttendanceResponse]:
    record = await service.update(principal, attendance_id, body)
    return success(AttendanceResponse.model_validate(record), "Attendance updated successfully")
