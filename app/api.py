"""Aggregates every resource router under one APIRouter (mounted at /api/v1 by app.main)."""

from fastapi import APIRouter

from app.routers import (
    assignments,
    attendance,
    auth,
    classes,
    courses,
    dashboard,
    departments,
    enrollments,
    grades,
    notifications,
    students,
    teachers,
    users,
)

api_router = APIRouter()

for _module in (
    auth,
    users,
    students,
    teachers,
    departments,
    courses,
    classes,
    enrollments,
    attendance,
    grades,
    assignments,
    notifications,
    dashboard,
):
    api_router.include_router(_module.router)
