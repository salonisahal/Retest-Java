"""Unauthenticated liveness and database health endpoints (outside the /api/v1 prefix)."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.dependencies import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health/db")
async def health_db(session: SessionDep) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("database health check failed")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected"})
    return JSONResponse(content={"status": "healthy", "database": "connected"})
