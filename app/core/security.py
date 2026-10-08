"""Password hashing and JWT creation/verification. Never logs credentials or tokens."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"
_CLOCK_SKEW_LEEWAY_SECONDS = 5


def hash_password(password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def hash_token(token: str) -> str:
    """Deterministic digest used to persist refresh tokens without storing them raw."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenPayload:
    user_id: UUID
    email: str
    role: str
    token_type: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedToken:
    token: str
    expires_at: datetime


def _encode(user_id: UUID, email: str, role: str, token_type: str, lifetime: timedelta) -> IssuedToken:
    settings = get_settings()
    expires_at = datetime.now(UTC) + lifetime
    claims = {
        "sub": str(user_id),
        "userId": str(user_id),
        "email": email,
        "role": role,
        "tokenType": token_type,
        "jti": uuid.uuid4().hex,
        "exp": expires_at,
    }
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return IssuedToken(token=token, expires_at=expires_at)


def create_access_token(user_id: UUID, email: str, role: str) -> IssuedToken:
    lifetime = timedelta(minutes=get_settings().jwt_access_token_expire_minutes)
    return _encode(user_id, email, role, ACCESS_TOKEN, lifetime)


def create_refresh_token(user_id: UUID, email: str, role: str) -> IssuedToken:
    lifetime = timedelta(days=get_settings().jwt_refresh_token_expire_days)
    return _encode(user_id, email, role, REFRESH_TOKEN, lifetime)


def decode_token(token: str, expected_type: str) -> TokenPayload:
    """Decode and validate a JWT; raises UnauthorizedError for any invalid/expired/wrong-type token."""
    settings = get_settings()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=_CLOCK_SKEW_LEEWAY_SECONDS,
            options={"require": ["exp", "userId", "tokenType"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc

    if claims["tokenType"] != expected_type:
        raise UnauthorizedError("Invalid token type")
    try:
        user_id = UUID(claims["userId"])
    except ValueError as exc:
        raise UnauthorizedError("Invalid authentication token") from exc
    return TokenPayload(
        user_id=user_id,
        email=claims.get("email", ""),
        role=claims.get("role", ""),
        token_type=claims["tokenType"],
        expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
    )
