import uuid

from app.models.student import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    model = Student

    async def get_by_user_id(self, user_id: uuid.UUID) -> Student | None:
        return await self.get_by(user_id=user_id)
