from app.models.grade import Grade
from app.repositories.base import BaseRepository


class GradeRepository(BaseRepository[Grade]):
    model = Grade
