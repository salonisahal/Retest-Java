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

## Decisions
- Tokens: access 30 min (`expiresIn` 1800), refresh 7 d, hashed (sha256) refresh tokens persisted in `refresh_tokens`, rotated on refresh, revoked on logout. Register creates STUDENT? -> register role defaults to STUDENT only (ADMIN/TEACHER creation via admin-only POST /users); register creates a bare user account.
- Login response data: `{accessToken, refreshToken, tokenType:"Bearer", expiresIn:1800, user:{...}}`.
