"""Database utilities for the thread service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .settings import get_settings

settings = get_settings()


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for ORM models."""


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for FastAPI dependencies."""

    async with SessionLocal() as session:
        yield session
