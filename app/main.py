"""FastAPI application factory and wiring."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.error_handlers import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.routers.health import router as health_router

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application starting")
    yield
    await engine.dispose()
    logger.info("application stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Student Management System REST API (JWT auth, RBAC: ADMIN / TEACHER / STUDENT).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"name": get_settings().app_name, "docs": "/docs"})
