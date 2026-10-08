import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AccessServiceDep, AdminOrTeacherPrincipal, CurrentPrincipal, SessionDep
from app.core.pagination import PageParamsDep, paged_success, success
from app.models.enums import ScheduleDay
from app.repositories.class_repository import ClassRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.base import ApiResponse, PagedApiResponse
from app.schemas.class_session import ClassRequest, ClassResponse
from app.services.class_service import ClassService

router = APIRouter(prefix="/classes", tags=["Classes"])


def get_class_service(session: SessionDep, access: AccessServiceDep) -> ClassService:
    return ClassService(session, ClassRepository(session), TeacherRepository(session), access)


ClassServiceDep = Annotated[ClassService, Depends(get_class_service)]


@router.get("", response_model=PagedApiResponse[ClassResponse], summary="List scheduled classes")
async def list_classes(
    _: CurrentPrincipal,
    service: ClassServiceDep,
    params: PageParamsDep,
    course_id: Annotated[uuid.UUID | None, Query(alias="courseId")] = None,
    teacher_id: Annotated[uuid.UUID | None, Query(alias="teacherId")] = None,
    schedule_day: Annotated[ScheduleDay | None, Query(alias="scheduleDay")] = None,
):
    page = await service.list_classes(params, course_id, teacher_id, schedule_day)
    return paged_success(page.map(ClassResponse.model_validate), "Classes retrieved successfully")


@router.get("/{class_id}", response_model=ApiResponse[ClassResponse], summary="Get a class")
async def get_class(class_id: uuid.UUID, _: CurrentPrincipal, service: ClassServiceDep):
    entity = await service.get_class(class_id)
    return success(ClassResponse.model_validate(entity), "Class retrieved successfully")


@router.post(
    "",
    response_model=ApiResponse[ClassResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a class (ADMIN/course teacher)",
)
async def create_class(request: ClassRequest, principal: AdminOrTeacherPrincipal, service: ClassServiceDep):
    entity = await service.create_class(principal, request)
    return success(ClassResponse.model_validate(entity), "Class created successfully")


@router.put("/{class_id}", response_model=ApiResponse[ClassResponse], summary="Update a class (ADMIN/course teacher)")
async def update_class(
    class_id: uuid.UUID, request: ClassRequest, principal: AdminOrTeacherPrincipal, service: ClassServiceDep
):
    entity = await service.update_class(principal, class_id, request)
    return success(ClassResponse.model_validate(entity), "Class updated successfully")


@router.delete("/{class_id}", response_model=ApiResponse[None], summary="Delete a class (ADMIN/course teacher)")
async def delete_class(class_id: uuid.UUID, principal: AdminOrTeacherPrincipal, service: ClassServiceDep):
    await service.delete_class(principal, class_id)
    return success(None, "Class deleted successfully")
