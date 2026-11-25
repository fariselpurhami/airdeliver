# backend/api/app/db/session.py

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Final

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from app.core.config import get_core_settings

settings = get_core_settings()

DEFAULT_POOL_SIZE: Final[int] = settings.DB_POOL_SIZE
DEFAULT_MAX_OVERFLOW: Final[int] = settings.DB_MAX_OVERFLOW
DEFAULT_POOL_RECYCLE_SECONDS: Final[int] = 1800
DEFAULT_POOL_TIMEOUT_SECONDS: Final[int] = 30


def _build_sync_database_uri(async_uri: str) -> str:
    if async_uri.startswith("postgresql+asyncpg://"):
        return async_uri.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if async_uri.startswith("postgresql+psycopg://"):
        return async_uri
    raise ValueError("Unsupported database URI scheme for synchronous engine construction.")


ASYNC_DATABASE_URI: Final[str] = str(settings.DATABASE_URI)
SYNC_DATABASE_URI: Final[str] = _build_sync_database_uri(ASYNC_DATABASE_URI)

async_engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=DEFAULT_POOL_SIZE,
    max_overflow=DEFAULT_MAX_OVERFLOW,
    pool_recycle=DEFAULT_POOL_RECYCLE_SECONDS,
    pool_timeout=DEFAULT_POOL_TIMEOUT_SECONDS,
    echo=False,
    future=True,
)

sync_engine = create_engine(
    SYNC_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=DEFAULT_POOL_SIZE,
    max_overflow=DEFAULT_MAX_OVERFLOW,
    pool_recycle=DEFAULT_POOL_RECYCLE_SECONDS,
    pool_timeout=DEFAULT_POOL_TIMEOUT_SECONDS,
    echo=False,
)

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

SyncSessionFactory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> Generator[Session, None, None]:
    with SyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
