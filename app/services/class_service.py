import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.pagination import Page, PageParams
from app.core.principal import Principal
from app.models.course import ClassSession
from app.models.enums import ScheduleDay
from app.repositories.class_repository import ClassRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.class_session import ClassRequest
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)


class ClassService:
    def __init__(
        self,
        session: AsyncSession,
        classes: ClassRepository,
        teachers: TeacherRepository,
        access: AccessService,
    ) -> None:
        self._session = session
        self._classes = classes
        self._teachers = teachers
        self._access = access

    async def list_classes(
        self,
        params: PageParams,
        course_id: uuid.UUID | None,
        teacher_id: uuid.UUID | None,
        schedule_day: ScheduleDay | None,
    ) -> Page[ClassSession]:
        return await self._classes.search(params, course_id, teacher_id, schedule_day)

    async def get_class(self, class_id: uuid.UUID) -> ClassSession:
        session_ = await self._classes.get(class_id)
        if session_ is None:
            raise NotFoundError("Class not found")
        return session_

    async def create_class(self, principal: Principal, request: ClassRequest) -> ClassSession:
        await self._access.assert_can_manage_course(principal, request.course_id)
        await self._check_teacher(principal, request)
        entity = ClassSession()
        self._apply(entity, request)
        await self._classes.add(entity)
        await self._session.commit()
        logger.info("class created", extra={"classId": str(entity.id)})
        return entity

    async def update_class(self, principal: Principal, class_id: uuid.UUID, request: ClassRequest) -> ClassSession:
        entity = await self.get_class(class_id)
        await self._access.assert_can_manage_course(principal, entity.course_id)
        if request.course_id != entity.course_id:
            await self._access.assert_can_manage_course(principal, request.course_id)
        await self._check_teacher(principal, request)
        self._apply(entity, request)
        await self._classes.flush()
        await self._session.commit()
        logger.info("class updated", extra={"classId": str(entity.id)})
        return entity

    async def delete_class(self, principal: Principal, class_id: uuid.UUID) -> None:
        entity = await self.get_class(class_id)
        await self._access.assert_can_manage_course(principal, entity.course_id)
        await self._classes.delete(entity)
        await self._session.commit()
        logger.info("class deleted", extra={"classId": str(class_id)})

    async def _check_teacher(self, principal: Principal, request: ClassRequest) -> None:
        if await self._teachers.get(request.teacher_id) is None:
            raise NotFoundError("Teacher not found")
        if principal.is_teacher and request.teacher_id != await self._access.teacher_id_for(principal):
            raise ForbiddenError("A teacher can only schedule classes for themselves")

    @staticmethod
    def _apply(entity: ClassSession, request: ClassRequest) -> None:
        entity.name = request.name
        entity.course_id = request.course_id
        entity.teacher_id = request.teacher_id
        entity.room = request.room
        entity.schedule_day = request.schedule_day
        entity.start_time = request.start_time
        entity.end_time = request.end_time
