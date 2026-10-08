# Student Management System API

FastAPI + async SQLAlchemy + PostgreSQL REST API with JWT auth and role-based access (ADMIN / TEACHER / STUDENT).

## Run with Docker
```
docker compose up -d --build   # API on http://localhost:8000, Swagger UI at /docs
```
The container applies Alembic migrations and seeds demo data on start.

## Run locally
```
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed.seed_data
uvicorn app.main:app --reload
```

## Seed credentials
| Role | Email | Password |
|---|---|---|
| Admin | admin@example.com | Admin@123 |
| Teacher | teacher1..4@example.com | Teacher@123 |
| Student | student1..24@example.com | Student@123 |

## API
Base path `/api/v1`: `auth`, `users`, `departments`, `teachers`, `students`, `courses`, `classes`, `enrollments`,
`attendance`, `grades`, `assignments`, `notifications`, `dashboard/{admin|teacher|student}`. `GET /health` is unauthenticated.
All responses use an envelope `{success, message, data, ...}`; lists add `pagination`; errors add `errorCode`, `errors`, `correlationId`.
List params: `page` (0-based), `size`, `search`, `sort=field,asc|desc`.

## Tests / lint
```
pytest        # needs Postgres DB `student_management_test`
ruff check app tests
```
