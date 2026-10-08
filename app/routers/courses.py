import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import (
    AccessServiceDep,
    AdminOrTeacherPrincipal,
    AdminPrincipal,
    CurrentPrincipal,
    SessionDep,
)
from app.core.pagination import PageParamsDep, paged_success, success
from app.repositories.course_repository import CourseRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.course import CourseRequest, CourseResponse
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["Courses"])


def get_course_service(session: SessionDep, access: AccessServiceDep) -> CourseService:
    return CourseService(
        session, CourseRepository(session), DepartmentRepository(session), TeacherRepository(session), access
    )


CourseServiceDep = Annotated[CourseService, Depends(get_course_service)]


@router.get("", response_model=PagedApiResponse[CourseResponse], summary="List courses")
async def list_courses(
    _: CurrentPrincipal,
    service: CourseServiceDep,
    params: PageParamsDep,
    department_id: Annotated[uuid.UUID | None, Query(alias="departmentId")] = None,
    teacher_id: Annotated[uuid.UUID | None, Query(alias="teacherId")] = None,
    semester: Annotated[int | None, Query(gt=0)] = None,
):
    page = await service.list_courses(params, department_id, teacher_id, semester)
    return paged_success(page.map(CourseResponse.model_validate), "Courses retrieved successfully")


@router.get("/{course_id}", response_model=ApiResponse[CourseResponse], summary="Get a course")
async def get_course(course_id: uuid.UUID, _: CurrentPrincipal, service: CourseServiceDep):
    course = await service.get_course(course_id)
    return success(CourseResponse.model_validate(course), "Course retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[CourseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a course (ADMIN)",
)
async def create_course(request: CourseRequest, _: AdminPrincipal, service: CourseServiceDep):
    course = await service.create_course(request)
    return success(CourseResponse.model_validate(course), "Course created successfully")


@router.put("/{course_id}", response_model=ApiResponse[CourseResponse], summary="Update a course (ADMIN/owner)")
async def update_course(
    course_id: uuid.UUID, request: CourseRequest, principal: AdminOrTeacherPrincipal, service: CourseServiceDep
):
    course = await service.update_course(principal, course_id, request)
    return success(CourseResponse.model_validate(course), "Course updated successfully")


@router.delete("/{course_id}", response_model=ApiResponse[None], summary="Delete a course (ADMIN/owner)")
async def delete_course(course_id: uuid.UUID, principal: AdminOrTeacherPrincipal, service: CourseServiceDep):
    await service.delete_course(principal, course_id)
    return success(None, "Course deleted successfully")
