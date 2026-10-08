import uuid

from app.models.teacher import Teacher
from app.repositories.base import BaseRepository


class TeacherRepository(BaseRepository[Teacher]):
    model = Teacher

    async def get_by_user_id(self, user_id: uuid.UUID) -> Teacher | None:
        return await self.get_by(user_id=user_id)
