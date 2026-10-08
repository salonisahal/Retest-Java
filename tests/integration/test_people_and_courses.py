import httpx

from tests.conftest import API, create_student, uid


async def test_department_conflict_and_not_found(
    client: httpx.AsyncClient, admin_headers: dict, department: dict
) -> None:
    duplicate = await client.post(
        f"{API}/departments", json={"name": department["name"], "code": f"X{uid()}"}, headers=admin_headers
    )
    assert duplicate.status_code == 409
    missing = await client.get(f"{API}/departments/00000000-0000-0000-0000-000000000000", headers=admin_headers)
    assert missing.status_code == 404
    assert missing.json()["errorCode"] == "NOT_FOUND"
    assert (await client.get(f"{API}/departments/not-a-uuid", headers=admin_headers)).status_code == 422


async def test_department_requires_admin_for_write(client: httpx.AsyncClient, student_headers: dict) -> None:
    response = await client.post(f"{API}/departments", json={"name": "N", "code": "N1"}, headers=student_headers)
    assert response.status_code == 403


async def test_department_list_search_and_pagination(
    client: httpx.AsyncClient, admin_headers: dict, department: dict
) -> None:
    response = await client.get(f"{API}/departments?search={department['code']}&page=0&size=10", headers=admin_headers)
    body = response.json()
    assert response.status_code == 200
    assert body["pagination"]["totalElements"] == 1
    assert body["data"][0]["id"] == department["id"]


async def test_invalid_sort_field_is_400(client: httpx.AsyncClient, admin_headers: dict) -> None:
    response = await client.get(f"{API}/departments?sort=bogus,asc", headers=admin_headers)
    assert response.status_code == 400


async def test_teacher_create_validates_and_conflicts(
    client: httpx.AsyncClient, admin_headers: dict, teacher: dict, department: dict
) -> None:
    payload = {
        "firstName": "T",
        "lastName": "Two",
        "email": teacher["email"],
        "password": "Teacher@123",
        "employeeId": f"E{uid()}",
        "departmentId": department["id"],
        "specialization": "Math",
    }
    assert (await client.post(f"{API}/teachers", json=payload, headers=admin_headers)).status_code == 409
    payload["email"] = f"t-{uid()}@example.com"
    payload["departmentId"] = "00000000-0000-0000-0000-000000000000"
    assert (await client.post(f"{API}/teachers", json=payload, headers=admin_headers)).status_code == 404


async def test_teacher_cannot_create_teacher(client: httpx.AsyncClient, teacher_headers: dict) -> None:
    response = await client.post(f"{API}/teachers", json={}, headers=teacher_headers)
    assert response.status_code == 403


async def test_student_scoping(
    client: httpx.AsyncClient, admin_headers: dict, student: dict, student_headers: dict, department: dict
) -> None:
    other = await create_student(client, admin_headers, department["id"])
    own = await client.get(f"{API}/students/{student['id']}", headers=student_headers)
    assert own.status_code == 200
    assert (await client.get(f"{API}/students/{other['id']}", headers=student_headers)).status_code == 403
    listing = await client.get(f"{API}/students", headers=student_headers)
    assert [row["id"] for row in listing.json()["data"]] == [student["id"]]


async def test_student_validation_and_status_update(
    client: httpx.AsyncClient, admin_headers: dict, department: dict
) -> None:
    bad = await client.post(
        f"{API}/students",
        json={
            "firstName": "B",
            "lastName": "Bad",
            "email": f"b-{uid()}@example.com",
            "password": "Student@123",
            "studentId": f"S{uid()}",
            "departmentId": department["id"],
            "semester": 0,
        },
        headers=admin_headers,
    )
    assert bad.status_code == 422
    assert "semester" in bad.json()["errors"]
    created = await create_student(client, admin_headers, department["id"])
    patched = await client.patch(
        f"{API}/students/{created['id']}/status", json={"status": "SUSPENDED"}, headers=admin_headers
    )
    assert patched.json()["data"]["status"] == "SUSPENDED"
    assert (await client.delete(f"{API}/students/{created['id']}", headers=admin_headers)).status_code == 200
