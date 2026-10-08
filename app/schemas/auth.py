"""Authentication DTOs."""

from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import CamelModel
from app.schemas.user import (
    NameStr,
    PasswordStr,
    PhoneStr,
    UserResponse,
    normalise_email,
    validate_password_bytes,
)


class LoginRequest(CamelModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return normalise_email(value)


class RegisterRequest(CamelModel):
    """Self-registration. There is deliberately no ``role`` field: public sign-ups are always STUDENT."""

    first_name: NameStr
    last_name: NameStr
    email: EmailStr
    password: PasswordStr
    phone: PhoneStr

    _check_password = field_validator("password")(validate_password_bytes)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return normalise_email(value)

    @field_validator("phone")
    @classmethod
    def _blank_phone_to_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class RefreshTokenRequest(CamelModel):
    refresh_token: Annotated[str, Field(min_length=1, max_length=4096)]


class LogoutRequest(RefreshTokenRequest):
    pass


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
