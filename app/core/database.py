"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    options: dict = {"pool_pre_ping": True}
    if settings.environment == "test":
        # Each pytest test runs on its own event loop; pooled connections cannot be shared.
        options["poolclass"] = NullPool
    return create_async_engine(settings.database_url, **options)


engine: AsyncEngine = _build_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session; services commit explicitly, errors roll back."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
