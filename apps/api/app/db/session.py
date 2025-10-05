# file: apps/api/app/db/session.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini 2.5 Pro

from sqlmodel import create_engine, Session

from app.core.config import settings

engine = create_engine(settings.DATABASE_URI, pool_pre_ping=True)

def get_session():
    with Session(engine) as session:
        yield session
