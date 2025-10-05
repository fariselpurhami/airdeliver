# This line MUST be the first import to ensure all models are loaded correctly.
from app.db import base  # noqa: F401

from fastapi import FastAPI
from sqlmodel import SQLModel
from app.db.session import engine
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.websockets.tracking_ws import router as tracking_router

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(
    title="airdeliver API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(tracking_router, prefix="/ws")

@app.get("/")
def read_root():
    return {"message": "Welcome to airdeliver API"}
