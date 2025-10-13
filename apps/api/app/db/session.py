# file: apps/api/app/db/session.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini 2.5 Pro

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from sqlmodel import create_engine, Session


engine = create_engine(settings.DATABASE_URI, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    with Session(engine) as session:
        yield session
