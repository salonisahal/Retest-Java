from app.models.course import ClassSession
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository[ClassSession]):
    model = ClassSession
