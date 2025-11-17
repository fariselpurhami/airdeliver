# apps/api/app/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings
from typing import AsyncGenerator
from sqlalchemy.orm import sessionmaker

engine: AsyncEngine = create_async_engine(settings.DATABASE_URI, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
