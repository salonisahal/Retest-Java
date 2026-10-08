"""Pure unit tests: password hashing, JWT handling, grade letters and pagination primitives (no HTTP)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.pagination import Page, PageParams, get_page_params, paged_success, success
from app.core.security import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.grade_calculator import calculate_grade_letter


# ---------------------------------------------------------------- passwords
def test_password_hash_roundtrip_and_salting() -> None:
    first = hash_password("Secret@123")
    second = hash_password("Secret@123")
    assert first != "Secret@123"
    assert first != second  # salted
    assert verify_password("Secret@123", first)
    assert not verify_password("wrong", first)


def test_verify_password_with_malformed_hash_is_false() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_hash_token_is_deterministic_sha256() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
    assert len(hash_token("abc")) == 64


# ---------------------------------------------------------------- jwt
def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    issued = create_access_token(user_id, "a@example.com", "ADMIN")
    payload = decode_token(issued.token, ACCESS_TOKEN)
    assert payload.user_id == user_id
    assert payload.email == "a@example.com"
    assert payload.role == "ADMIN"
    assert payload.token_type == ACCESS_TOKEN
    assert payload.expires_at > datetime.now(UTC)


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    issued = create_refresh_token(uuid.uuid4(), "a@example.com", "STUDENT")
    assert decode_token(issued.token, REFRESH_TOKEN).token_type == REFRESH_TOKEN
    with pytest.raises(UnauthorizedError):
        decode_token(issued.token, ACCESS_TOKEN)


def test_tampered_or_garbage_token_is_rejected() -> None:
    issued = create_access_token(uuid.uuid4(), "a@example.com", "ADMIN")
    with pytest.raises(UnauthorizedError):
        decode_token(issued.token + "x", ACCESS_TOKEN)
    with pytest.raises(UnauthorizedError):
        decode_token("garbage", ACCESS_TOKEN)


def test_token_signed_with_other_key_is_rejected() -> None:
    settings = get_settings()
    forged = jwt.encode(
        {
            "userId": str(uuid.uuid4()),
            "tokenType": ACCESS_TOKEN,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "some-other-secret-key-of-sufficient-length",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError):
        decode_token(forged, ACCESS_TOKEN)


def test_expired_token_is_rejected() -> None:
    settings = get_settings()
    expired = jwt.encode(
        {
            "userId": str(uuid.uuid4()),
            "tokenType": ACCESS_TOKEN,
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(UnauthorizedError, match="expired"):
        decode_token(expired, ACCESS_TOKEN)


# ---------------------------------------------------------------- grading
@pytest.mark.parametrize(
    ("marks", "max_marks", "letter"),
    [
        (100, 100, "A+"),
        (90, 100, "A+"),
        (89.99, 100, "A"),
        (80, 100, "A"),
        (70, 100, "B"),
        (60, 100, "C"),
        (50, 100, "D"),
        (49, 100, "F"),
        (0, 100, "F"),
        (9, 10, "A+"),  # exact boundary despite float noise
        (45, 50, "A+"),
        (35, 50, "B"),
    ],
)
def test_grade_letter_bands(marks: float, max_marks: float, letter: str) -> None:
    assert calculate_grade_letter(marks, max_marks) == letter


@pytest.mark.parametrize("max_marks", [0, -10])
def test_grade_letter_rejects_non_positive_max(max_marks: float) -> None:
    with pytest.raises(ValueError):
        calculate_grade_letter(10, max_marks)


# ---------------------------------------------------------------- pagination
def test_page_params_offset_and_defaults() -> None:
    params = PageParams(page=3, size=10)
    assert params.offset == 30
    assert get_page_params(page=0, size=20, search="  ", sort=None).search is None
    assert get_page_params(page=0, size=20, search=" math ", sort="name,asc").search == "math"


def test_page_total_pages_and_map() -> None:
    page = Page(items=[1, 2, 3], total=45, page=0, size=20)
    assert page.total_pages == 3
    assert page.map(lambda n: n * 2).items == [2, 4, 6]
    assert Page(items=[], total=0, page=0, size=20).total_pages == 0


def test_envelope_builders() -> None:
    ok = success({"a": 1}, "done")
    assert ok.success is True and ok.message == "done" and ok.data == {"a": 1}
    paged = paged_success(Page(items=[1, 2], total=2, page=0, size=20))
    dumped = paged.model_dump(by_alias=True)
    assert dumped["pagination"]["totalElements"] == 2
    assert dumped["pagination"]["totalPages"] == 1


# ---------------------------------------------------------------- settings
def test_production_rejects_default_or_short_jwt_secret() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret_key="change-me-in-production")
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret_key="short")
    assert Settings(environment="production", jwt_secret_key="x" * 40).jwt_secret_key == "x" * 40
    assert Settings(environment="development").environment == "development"
