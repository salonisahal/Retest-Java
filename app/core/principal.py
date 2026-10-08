"""The authenticated caller, as resolved from a verified access token."""

from dataclasses import dataclass
from uuid import UUID

from app.models.enums import UserRole


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def is_teacher(self) -> bool:
        return self.role is UserRole.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role is UserRole.STUDENT
