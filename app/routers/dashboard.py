"""Role-specific dashboards (read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import AccessServiceDep, AdminPrincipal, SessionDep, require_roles
from app.core.pagination import success
from app.core.principal import Principal
from app.models.enums import UserRole
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.base import ApiResponse
from app.schemas.dashboard import AdminDashboardResponse, StudentDashboardResponse, TeacherDashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

TeacherPrincipal = Annotated[Principal, Depends(require_roles(UserRole.TEACHER))]
StudentPrincipal = Annotated[Principal, Depends(require_roles(UserRole.STUDENT))]


def get_dashboard_service(session: SessionDep, access: AccessServiceDep) -> DashboardService:
    return DashboardService(DashboardRepository(session), access)


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/admin", response_model=ApiResponse[AdminDashboardResponse], summary="Admin dashboard")
async def admin_dashboard(
    principal: AdminPrincipal, service: DashboardServiceDep
) -> ApiResponse[AdminDashboardResponse]:
    return success(await service.admin(principal), "Admin dashboard retrieved")


@router.get("/teacher", response_model=ApiResponse[TeacherDashboardResponse], summary="Teacher dashboard")
async def teacher_dashboard(
    principal: TeacherPrincipal, service: DashboardServiceDep
) -> ApiResponse[TeacherDashboardResponse]:
    return success(await service.teacher(principal), "Teacher dashboard retrieved")


@router.get("/student", response_model=ApiResponse[StudentDashboardResponse], summary="Student dashboard")
async def student_dashboard(
    principal: StudentPrincipal, service: DashboardServiceDep
) -> ApiResponse[StudentDashboardResponse]:
    return success(await service.student(principal), "Student dashboard retrieved")
