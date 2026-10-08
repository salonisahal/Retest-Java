import httpx

from tests.conftest import API, create_student, uid


async def test_course_crud_and_rules(
    client: httpx.AsyncClient, admin_headers: dict, teacher_headers: dict, student_headers: dict, course: dict
) -> None:
    duplicate = {**course, "courseName": "Dup"}
    for key in ("id", "createdAt", "updatedAt"):
        duplicate.pop(key, None)
    assert (await client.post(f"{API}/courses", json=duplicate, headers=admin_headers)).status_code == 409
    assert (await client.post(f"{API}/courses", json=duplicate, headers=teacher_headers)).status_code == 403
    assert (await client.post(f"{API}/courses", json=duplicate, headers=student_headers)).status_code == 403
    invalid = await client.post(
        f"{API}/courses", json={**duplicate, "courseCode": uid(), "credits": 0}, headers=admin_headers
    )
    assert invalid.status_code == 422
    assert "credits" in invalid.json()["errors"]
    assert (await client.get(f"{API}/courses/{course['id']}", headers=student_headers)).status_code == 200


async def test_teacher_updates_own_course_but_cannot_reassign(
    client: httpx.AsyncClient, admin_headers: dict, teacher_headers: dict, teacher: dict, course: dict, department: dict
) -> None:
    body = {
        "courseCode": course["courseCode"],
        "courseName": "Renamed",
        "credits": 4,
        "departmentId": department["id"],
        "teacherId": teacher["id"],
        "semester": 1,
    }
    updated = await client.put(f"{API}/courses/{course['id']}", json=body, headers=teacher_headers)
    assert updated.status_code == 200
    assert updated.json()["data"]["courseName"] == "Renamed"


async def test_class_time_validation(
    client: httpx.AsyncClient, admin_headers: dict, course: dict, teacher: dict
) -> None:
    body = {
        "name": "Lecture 1",
        "courseId": course["id"],
        "teacherId": teacher["id"],
        "room": "R101",
        "scheduleDay": "MONDAY",
        "startTime": "10:00:00",
        "endTime": "09:00:00",
    }
    assert (await client.post(f"{API}/classes", json=body, headers=admin_headers)).status_code == 422
    body["endTime"] = "11:00:00"
    created = await client.post(f"{API}/classes", json=body, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["data"]["startTime"] == "10:00:00"


async def test_enrollment_flow_and_scoping(
    client: httpx.AsyncClient, admin_headers: dict, student: dict, student_headers: dict, course: dict, department: dict
) -> None:
    body = {"studentId": student["id"], "courseId": course["id"], "semester": 1}
    created = await client.post(f"{API}/enrollments", json=body, headers=admin_headers)
    assert created.status_code == 201
    assert (await client.post(f"{API}/enrollments", json=body, headers=admin_headers)).status_code == 409
    other = await create_student(client, admin_headers, department["id"])
    forbidden = await client.post(
        f"{API}/enrollments", json={**body, "studentId": other["id"]}, headers=student_headers
    )
    assert forbidden.status_code == 403
    listing = await client.get(f"{API}/enrollments", headers=student_headers)
    assert [row["studentId"] for row in listing.json()["data"]] == [student["id"]]
    missing = await client.post(
        f"{API}/enrollments",
        json={**body, "courseId": "00000000-0000-0000-0000-000000000000"},
        headers=admin_headers,
    )
    assert missing.status_code == 404


async def test_attendance_rules(
    client: httpx.AsyncClient,
    admin_headers: dict,
    teacher_headers: dict,
    student_headers: dict,
    student: dict,
    course: dict,
) -> None:
    body = {"studentId": student["id"], "courseId": course["id"], "date": "2025-01-15", "status": "PRESENT"}
    created = await client.post(f"{API}/attendance", json=body, headers=teacher_headers)
    assert created.status_code == 201
    assert created.json()["data"]["markedBy"] is not None
    assert (await client.post(f"{API}/attendance", json=body, headers=admin_headers)).status_code == 409
    assert (await client.post(f"{API}/attendance", json=body, headers=student_headers)).status_code == 403
    own = await client.get(f"{API}/students/{student['id']}/attendance", headers=student_headers)
    assert own.status_code == 200
    assert own.json()["pagination"]["totalElements"] >= 1
    course_view = await client.get(f"{API}/courses/{course['id']}/attendance", headers=student_headers)
    assert course_view.status_code == 403
    updated = await client.put(
        f"{API}/attendance/{created.json()['data']['id']}", json={"status": "LATE"}, headers=teacher_headers
    )
    assert updated.json()["data"]["status"] == "LATE"


async def test_grades_auto_letter_and_validation(
    client: httpx.AsyncClient,
    admin_headers: dict,
    teacher_headers: dict,
    student_headers: dict,
    student: dict,
    course: dict,
) -> None:
    body = {"studentId": student["id"], "courseId": course["id"], "marks": 85, "maxMarks": 100, "grade": "F"}
    created = await client.post(f"{API}/grades", json=body, headers=teacher_headers)
    assert created.status_code == 201
    assert created.json()["data"]["grade"] == "A"
    over = await client.post(f"{API}/grades", json={**body, "marks": 101}, headers=admin_headers)
    assert over.status_code == 422
    assert "marks" in over.json()["errors"]
    assert (await client.post(f"{API}/grades", json=body, headers=student_headers)).status_code == 403
    grade_id = created.json()["data"]["id"]
    updated = await client.put(f"{API}/grades/{grade_id}", json={"marks": 95}, headers=teacher_headers)
    assert updated.json()["data"]["grade"] == "A+"
    own = await client.get(f"{API}/grades", headers=student_headers)
    assert own.status_code == 200 and own.json()["pagination"]["totalElements"] >= 1


async def test_assignment_visibility_for_students(
    client: httpx.AsyncClient,
    admin_headers: dict,
    teacher_headers: dict,
    student_headers: dict,
    teacher: dict,
    course: dict,
) -> None:
    def body(title: str, status: str) -> dict:
        return {
            "title": title,
            "courseId": course["id"],
            "teacherId": teacher["id"],
            "dueDate": "2030-01-01T10:00:00Z",
            "maxMarks": 50,
            "status": status,
        }

    draft = await client.post(f"{API}/assignments", json=body("Draft HW", "DRAFT"), headers=teacher_headers)
    published = await client.post(f"{API}/assignments", json=body("Pub HW", "PUBLISHED"), headers=teacher_headers)
    assert draft.status_code == 201 and published.status_code == 201
    visible = await client.get(f"{API}/assignments", headers=student_headers)
    titles = {row["title"] for row in visible.json()["data"]}
    assert "Pub HW" in titles and "Draft HW" not in titles
    hidden = await client.get(f"{API}/assignments/{draft.json()['data']['id']}", headers=student_headers)
    assert hidden.status_code == 403
    zero = await client.post(f"{API}/assignments", json={**body("Bad", "DRAFT"), "maxMarks": 0}, headers=admin_headers)
    assert zero.status_code == 422


async def test_notifications_and_dashboards(
    client: httpx.AsyncClient, admin_headers: dict, teacher_headers: dict, student_headers: dict
) -> None:
    assert (await client.get(f"{API}/notifications", headers=student_headers)).status_code == 200
    read_all = await client.patch(f"{API}/notifications/read-all", headers=student_headers)
    assert read_all.status_code == 200
    missing = await client.patch(
        f"{API}/notifications/00000000-0000-0000-0000-000000000000/read", headers=student_headers
    )
    assert missing.status_code == 404
    admin_dash = await client.get(f"{API}/dashboard/admin", headers=admin_headers)
    assert admin_dash.status_code == 200
    assert admin_dash.json()["data"]["totalStudents"] >= 1
    assert (await client.get(f"{API}/dashboard/admin", headers=student_headers)).status_code == 403
    teacher_dash = await client.get(f"{API}/dashboard/teacher", headers=teacher_headers)
    assert teacher_dash.status_code == 200
    student_dash = await client.get(f"{API}/dashboard/student", headers=student_headers)
    assert student_dash.status_code == 200
    assert "attendanceSummary" in student_dash.json()["data"]
