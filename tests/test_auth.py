import httpx

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, API, uid


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_login_success_returns_tokens(client: httpx.AsyncClient, admin_headers: dict) -> None:
    response = await client.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["tokenType"] == "Bearer"
    assert body["data"]["expiresIn"] == 1800
    assert body["data"]["user"]["role"] == "ADMIN"
    assert "passwordHash" not in body["data"]["user"]


async def test_login_wrong_password_is_401(client: httpx.AsyncClient, admin_headers: dict) -> None:
    response = await client.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "nope-nope-1"})
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["errorCode"] == "UNAUTHORIZED"
    assert "correlationId" in body


async def test_login_validation_error_is_422(client: httpx.AsyncClient) -> None:
    response = await client.post(f"{API}/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    assert response.json()["errorCode"] == "VALIDATION_ERROR"


async def test_register_creates_student_and_rejects_duplicate(client: httpx.AsyncClient) -> None:
    payload = {"firstName": "Ann", "lastName": "Lee", "email": f"ann-{uid()}@example.com", "password": "Password@1"}
    created = await client.post(f"{API}/auth/register", json={**payload, "role": "ADMIN"})
    assert created.status_code == 201
    assert created.json()["data"]["role"] == "STUDENT"
    duplicate = await client.post(f"{API}/auth/register", json=payload)
    assert duplicate.status_code == 409


async def test_me_requires_authentication(client: httpx.AsyncClient, admin_headers: dict) -> None:
    assert (await client.get(f"{API}/auth/me")).status_code == 401
    me = await client.get(f"{API}/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["data"]["email"] == ADMIN_EMAIL


async def test_invalid_token_is_401(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


async def test_refresh_rotates_and_old_token_is_rejected(client: httpx.AsyncClient, admin_headers: dict) -> None:
    login = (await client.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})).json()
    old_refresh = login["data"]["refreshToken"]
    refreshed = await client.post(f"{API}/auth/refresh", json={"refreshToken": old_refresh})
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["refreshToken"] != old_refresh
    reused = await client.post(f"{API}/auth/refresh", json={"refreshToken": old_refresh})
    assert reused.status_code == 401


async def test_logout_revokes_refresh_token(client: httpx.AsyncClient, admin_headers: dict) -> None:
    login = (await client.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})).json()
    headers = {"Authorization": f"Bearer {login['data']['accessToken']}"}
    refresh = login["data"]["refreshToken"]
    assert (await client.post(f"{API}/auth/logout", json={"refreshToken": refresh}, headers=headers)).status_code == 200
    assert (await client.post(f"{API}/auth/refresh", json={"refreshToken": refresh})).status_code == 401


async def test_users_endpoints_are_admin_only(
    client: httpx.AsyncClient, admin_headers: dict, student_headers: dict
) -> None:
    assert (await client.get(f"{API}/users", headers=student_headers)).status_code == 403
    listing = await client.get(f"{API}/users?size=5&sort=email,asc", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["pagination"]["size"] == 5


async def test_admin_user_crud(client: httpx.AsyncClient, admin_headers: dict) -> None:
    payload = {
        "firstName": "Una",
        "lastName": "User",
        "email": f"una-{uid()}@example.com",
        "password": "Password@1",
        "role": "TEACHER",
    }
    created = await client.post(f"{API}/users", json=payload, headers=admin_headers)
    assert created.status_code == 201
    user_id = created.json()["data"]["id"]
    status = await client.patch(f"{API}/users/{user_id}/status", json={"status": "INACTIVE"}, headers=admin_headers)
    assert status.status_code == 200
    assert status.json()["data"]["status"] == "INACTIVE"
    assert (await client.delete(f"{API}/users/{user_id}", headers=admin_headers)).status_code == 200
    assert (await client.get(f"{API}/users/{user_id}", headers=admin_headers)).status_code == 404
