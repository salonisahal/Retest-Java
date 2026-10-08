"""Pytest fixtures: isolated test database, ASGI client, role-based auth headers and API-driven data factories."""

import os
import uuid
from collections.abc import AsyncIterator

os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/student_management_test")
os.environ["BCRYPT_ROUNDS"] = "4"

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

API = "/api/v1"
ADMIN_EMAIL = "admin-test@example.com"
ADMIN_PASSWORD = "Admin@1234"


def uid() -> str:
    return uuid.uuid4().hex[:8]


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def client(_database: None) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict:
    response = await client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest_asyncio.fixture(scope="session")
async def admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    from app.core.database import SessionFactory
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    async with SessionFactory() as session:
        session.add(
            User(
                first_name="Test",
                last_name="Admin",
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
        )
        await session.commit()
    tokens = await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


@pytest_asyncio.fixture(scope="session")
async def department(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict:
    suffix = uid()
    response = await client.post(
        f"{API}/departments", json={"name": f"Dept {suffix}", "code": f"D{suffix}"}, headers=admin_headers
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest_asyncio.fixture(scope="session")
async def teacher(client: httpx.AsyncClient, admin_headers: dict[str, str], department: dict) -> dict:
    suffix = uid()
    payload = {
        "firstName": "Terry",
        "lastName": "Teacher",
        "email": f"teacher-{suffix}@example.com",
        "password": "Teacher@123",
        "employeeId": f"EMP{suffix}",
        "departmentId": department["id"],
        "specialization": "Algorithms",
    }
    response = await client.post(f"{API}/teachers", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return {**response.json()["data"], "password": payload["password"]}


@pytest_asyncio.fixture(scope="session")
async def teacher_headers(client: httpx.AsyncClient, teacher: dict) -> dict[str, str]:
    tokens = await _login(client, teacher["email"], teacher["password"])
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


async def create_student(client: httpx.AsyncClient, admin_headers: dict, department_id: str) -> dict:
    suffix = uid()
    payload = {
        "firstName": "Sam",
        "lastName": "Student",
        "email": f"student-{suffix}@example.com",
        "password": "Student@123",
        "studentId": f"STU{suffix}",
        "departmentId": department_id,
        "semester": 1,
    }
    response = await client.post(f"{API}/students", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return {**response.json()["data"], "password": payload["password"]}


@pytest_asyncio.fixture(scope="session")
async def student(client: httpx.AsyncClient, admin_headers: dict[str, str], department: dict) -> dict:
    return await create_student(client, admin_headers, department["id"])


@pytest_asyncio.fixture(scope="session")
async def student_headers(client: httpx.AsyncClient, student: dict) -> dict[str, str]:
    tokens = await _login(client, student["email"], student["password"])
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


@pytest_asyncio.fixture(scope="session")
async def course(client: httpx.AsyncClient, admin_headers: dict[str, str], department: dict, teacher: dict) -> dict:
    suffix = uid()
    payload = {
        "courseCode": f"C{suffix}",
        "courseName": "Data Structures",
        "credits": 3,
        "departmentId": department["id"],
        "teacherId": teacher["id"],
        "semester": 1,
    }
    response = await client.post(f"{API}/courses", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.fixture
def api() -> str:
    return API
