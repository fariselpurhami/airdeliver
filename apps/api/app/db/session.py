# apps/api/app/db/session.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings
from typing import AsyncGenerator
from sqlmodel import Session 

engine: AsyncEngine = create_async_engine(settings.DATABASE_URI, pool_pre_ping=True)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session

def get_sync_session():
    
    with Session(engine) as session:
        yield session
