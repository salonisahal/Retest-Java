"""User DTOs. ``passwordHash`` is never part of any response model."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from app.models.enums import UserRole, UserStatus
from app.schemas.base import CamelModel

MAX_PASSWORD_BYTES = 72  # bcrypt input limit

NameStr = Annotated[str, Field(min_length=1, max_length=100, description="Name (1-100 chars)")]
PhoneStr = Annotated[str | None, Field(default=None, max_length=30, description="Phone number")]
PasswordStr = Annotated[str, Field(min_length=8, max_length=128, description="Password (min 8 chars)")]


def validate_password_bytes(value: str | None) -> str | None:
    """bcrypt only accepts up to 72 bytes; reject longer input instead of failing at hashing time."""
    if value is not None and len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return value


def normalise_email(value: str) -> str:
    return value.strip().lower()


class UserResponse(CamelModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class _UserWriteBase(CamelModel):
    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    phone: PhoneStr

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return normalise_email(value)

    @field_validator("phone")
    @classmethod
    def _blank_phone_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class UserCreateRequest(_UserWriteBase):
    password: PasswordStr
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE

    _check_password = field_validator("password")(validate_password_bytes)


class UserUpdateRequest(_UserWriteBase):
    """Full replace of the editable fields; ``password`` is optional (rehashed when supplied)."""

    password: Annotated[str | None, Field(default=None, min_length=8, max_length=128)]
    role: UserRole
    status: UserStatus

    _check_password = field_validator("password")(validate_password_bytes)


class UserStatusUpdateRequest(CamelModel):
    status: UserStatus
