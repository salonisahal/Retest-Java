# checkpoint — job-dad3a545-fc3d-41c5-9f2b-c4da2fde70ee

Project dir: `/outputs/job-dad3a545-fc3d-41c5-9f2b-c4da2fde70ee` (FastAPI 0.115.6, Py 3.13, SQLAlchemy 2 async, asyncpg, Alembic, Pydantic 2).
Environment: NO docker daemon on host (docker_pull/compose unusable) -> Postgres 17 installed natively via apt, running on localhost:5432
(user postgres/postgres; DBs `student_management`, `student_management_test`). Start with `service postgresql start` if down.
Run python natively (`python`, `pytest`, `ruff`, `alembic`). Dockerfile/compose are written but cannot be built/run here -> report honestly.

## Status
| Step | State |
|---|---|
| 1 design / scaffold core (config, db, exceptions, error handlers, logging, security, pagination, base repo) | DONE |
| 2 models + alembic migration 0001 (applied OK to student_management) | DONE |
| repositories (all 12 + BaseRepository), AccessService, dependencies, health router, main.py, app/api.py | DONE |
| 3 schemas/services/routers per group (A-E below) | IN PROGRESS (subagents) |
| seed, tests, Dockerfile, compose, README, .env.example, pyproject (ruff) | TODO |
| boot verify, pytest, ruff, reports (tests-artifacts/), final | TODO |

## Conventions (all groups MUST follow)
- Layers: `app/routers/<x>.py` (thin, `router = APIRouter(prefix="/<x>", tags=["<X>"])`, NO prefix /api/v1 - app.main mounts it) -> `app/services/<x>_service.py` (class, takes `AsyncSession`/repos in ctor, owns commit) -> `app/repositories/*` -> models. DTOs in `app/schemas/<x>.py` (all inherit `app.schemas.base.CamelModel`; never return ORM models).
- DI: router file defines `def get_<x>_service(session: SessionDep) -> XService` and uses `Annotated[XService, Depends(...)]`. Use `SessionDep, CurrentPrincipal, AdminPrincipal, AdminOrTeacherPrincipal, AccessServiceDep, require_roles` from `app.core.dependencies`. `Principal` (app.core.principal): user_id, email, role, is_admin/is_teacher/is_student.
- Responses: `response_model=ApiResponse[XResponse]` and return `success(data, "msg")`; lists: `PagedApiResponse[XResponse]` + `paged_success(page.map(XResponse.model_validate), ...)` (`app.core.pagination`). POST -> 201. DELETE -> 200 envelope with data null. List params via `PageParamsDep` (page 0-based, size 20, search, sort="field,dir"). Sorting through `BaseRepository.paginate(stmt, params, sortable={"apiFieldName": Model.col}, default_sort=[...])` (unknown field -> 400); search via `BaseRepository.search_clause(search, [cols])`.
- Errors: raise `NotFoundError/ConflictError/ForbiddenError/BadRequestError/ValidationFailedError` (app.core.exceptions). Missing FK referenced in a body -> NotFoundError("<Entity> not found"). Duplicate unique value -> ConflictError (pre-check; IntegrityError also maps to 409 globally). Pydantic Field constraints give 422 (credits>0, semester>0, maxMarks>0, 0<=marks, start<end via model_validator).
- Services commit explicitly (`await self._session.commit()`) after writes; multi-entity writes (user+student, user+teacher) in ONE transaction (flush, then single commit). Use `logging.getLogger(__name__)`; never log passwords/tokens. `hash_password` from `app.core.security`.
- IDs are uuid.UUID (path params typed `uuid.UUID`; invalid -> 422). Enum values in `app.models.enums`.
- AccessService (app/services/access_service.py): `teacher_id_for(principal)`, `student_id_for(principal)`, `teacher_course_ids(principal)`, `assert_can_manage_course(principal, course_id)` (ADMIN ok; TEACHER only own course; else 403; missing course 404). Teacher "own" = Course.teacher_id == Teacher.id (profile id, NOT user id).
- Student-visible scoping: STUDENT sees only rows for their own student profile (`student_id_for`); a student reading someone else's single row -> 403 (lists are filtered silently). TEACHER list views of attendance/grades/assignments/enrollments are filtered to their courses.
- Pre-existing helper contract: `app/services/grade_calculator.py::calculate_grade_letter(marks: float, max_marks: float) -> str` (A+ >=90%, A >=80, B >=70, C >=60, D >=50, else F) written by group D; seed imports it.
- Notification helper contract (group E): `NotificationService.create_for_user(user_id, title, message, type)` (not required by others).
- Lint: ruff, line-length 120 (pyproject.toml written by parent). Run `ruff check app && ruff format app` on your files.
- Do NOT edit files outside your group (core/, models/, repositories/base.py, dependencies.py, main.py, api.py, routers/__init__.py). If a repository needs extra query methods, add them to that entity's own repository file (only your group's repos).
- Do not import `app.api`/`app.main` in module-level code of your files (other groups' routers may not exist yet); verify with `python -c "import app.routers.<x>"`.

## Groups / ownership
- A: auth (`routers/auth.py` /auth/login,register,refresh,logout,me), users (`routers/users.py`). services/auth_service.py, user_service.py; schemas/auth.py, user.py. Repos: user_repository, refresh_token_repository.
- B: departments, teachers, students (routers + services + schemas). Repos: department, teacher, student.
- C: courses, classes, enrollments. Repos: course, class, enrollment. (courses router has NO attendance endpoint; see D.)
- D: attendance (router declares FULL paths: `/attendance`, `/attendance/{id}`, `/students/{student_id}/attendance`, `/courses/{course_id}/attendance`), grades, assignments + grade_calculator. Repos: attendance, grade, assignment.
- E: notifications (`/notifications`, `/notifications/read-all` BEFORE `/{id}`, `/{id}/read`, DELETE), dashboard (`/dashboard/admin|teacher|student`), seed (`app/seed/seed_data.py`, idempotent, `python -m app.seed.seed_data`). Repos: notification (+ queries for dashboard in a new `app/repositories/dashboard_repository.py`).

## Group C status (courses/classes/enrollments): WRITTEN, NOT EXECUTED
- Files: schemas/{course,class_session,enrollment}.py; services/{course,class,enrollment}_service.py; routers/{courses,classes,enrollments}.py; repos course/class/enrollment got `search(...)` (+ `get_by_code`, `get_by_unique_key`).
- The subagent had NO shell tool: import check, ruff check/format and the throwaway httpx tests were NOT run. Parent must run `python -c "import app.routers.courses, app.routers.classes, app.routers.enrollments"` and `ruff check app && ruff format app`, then smoke-test.
- Behaviours: student self-enroll forces status ACTIVE; teacher POST/PUT class requires teacherId == own profile id (403); non-admin course PUT cannot change teacherId (403); enrollments `search` param ignored (no text fields).

## Decisions
- Tokens: access 30 min (`expiresIn` 1800), refresh 7 d, hashed (sha256) refresh tokens persisted in `refresh_tokens`, rotated on refresh, revoked on logout. Register creates STUDENT? -> register role defaults to STUDENT only (ADMIN/TEACHER creation via admin-only POST /users); register creates a bare user account.
- Group E (notifications/dashboard/seed): files written (schemas/{notification,dashboard}.py, services/{notification,dashboard}_service.py, repositories/{notification,dashboard}_repository.py, routers/{notifications,dashboard}.py, seed/seed_data.py). `NotificationService(session).create_for_user(user_id, title, message, type)` adds+flushes, caller commits. Dashboard routers need `app.routers.notifications.router` / `app.routers.dashboard.router` registered in app/api.py. **NOT executed**: the Group E subagent had only file tools (no shell) -> import check, ruff, route tests and the seed run are UNVERIFIED; parent must run `python -c "import app.routers.notifications, app.routers.dashboard"`, `ruff check app && ruff format app`, `python -m app.seed.seed_data` (twice).
- Seed creds: admin@example.com/Admin@123; teacher1..4@example.com/Teacher@123 (EMP0001..4); student1..24@example.com/Student@123 (STU0001..24). Expected counts: 4 depts, 12 courses, 72 enrollments, 24 students, 4 teachers, 29 users.
- Login response data: `{accessToken, refreshToken, tokenType:"Bearer", expiresIn:1800, user:{...}}`.

## Group A (auth + users) — CODE WRITTEN, NOT EXECUTED
Files: schemas/{auth,user}.py, services/{auth_service,user_service}.py, routers/{auth,users}.py; repo additions: `UserRepository.email_taken/search/USER_SORTABLE`, `RefreshTokenRepository.revoke_if_active/revoke_all_for_user`.
This subagent had NO shell tool (only file read/write), so import check, `ruff check/format`, and the httpx smoke test were NOT run -> parent must run `python -c "import app.routers.auth, app.routers.users"`, `ruff check app && ruff format app`, and exercise endpoints.
Behaviour notes: login returns identical 401 for unknown email/wrong password/INACTIVE; register has no role field (always STUDENT); emails lowercased; password max 72 bytes (bcrypt); refresh rotation uses atomic conditional UPDATE (reuse -> 401); logout only revokes caller's own token (unknown/foreign = idempotent 200); deactivating a user or resetting password revokes all their refresh tokens; `DELETE /users/{id}` self -> 400. Note: email-validator rejects special-use domains (e.g. `@x.test`, `@example.com` ok? `.test`/`.example` TLDs are rejected) -> seed/test emails must use real-looking domains.

## Group B (departments + teachers + students) — CODE WRITTEN, NOT EXECUTED
Files: schemas/{department,teacher,student}.py; services/{department,teacher,student}_service.py; routers/{departments,teachers,students}.py. Repositories (department/teacher/student) were already complete (search, name_taken/code_taken/count_references, employee_id_taken/count_assignments_of, student_id_taken/get_by_user_id/get_fresh) and were NOT modified.
This subagent has NO shell tool (only ls/read/write/edit/glob/grep), so import check, `ruff check/format` and the httpx smoke test were NOT run -> parent must run `python -c "import app.routers.departments, app.routers.teachers, app.routers.students"`, `ruff check app && ruff format app`, then exercise the endpoints.
Endpoints (mounted at /api/v1):
- Departments: GET `/departments` (any auth; search name/code; sort id,name,code,createdAt), GET `/departments/{id}`, POST (ADMIN, 201; 409 dup name/code; headTeacherId must exist -> 404), PUT `/{id}` (ADMIN), DELETE `/{id}` (ADMIN; 409 if referenced by teachers/students/courses).
- Teachers: GET list (ADMIN/TEACHER; filter `departmentId`; search; sort), GET `/{id}`, POST (ADMIN; user role TEACHER + profile in one transaction; 409 dup email/employeeId; dept 404), PUT `/{id}` (ADMIN; user fields + profile), DELETE `/{id}` (ADMIN; removes profile+user; 409 if assigned to courses/classes/assignments). `status` is a free string, upper-cased, default ACTIVE.
- Students: GET list (ADMIN/TEACHER all + filters `departmentId`, `semester`, `status`; STUDENT silently filtered to own record), GET `/{id}` (STUDENT other's -> 403), POST (ADMIN; user role STUDENT + profile one transaction; 409 dup email/studentId; dept 404; semester>0), PUT `/{id}` (ADMIN), PATCH `/{id}/status` (ADMIN, body `{status}`), DELETE `/{id}` (ADMIN; removes profile+user). `GET /students/{id}/attendance` is group D's.
Notes: DTOs built via `TeacherResponse.from_entity` / `StudentResponse.from_entity` (user relationship is selectin-loaded); after PUT/PATCH the entity is reloaded via `get_fresh` (populate_existing) before returning; emails lowercased; passwords 8..72 chars, never returned.
