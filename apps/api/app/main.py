# file: apps/api/app/main.py

# This line MUST be the first import
from app.db import base  # noqa: F401

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

# --- THIS IS THE NEW MIDDLEWARE YOU DESIGNED ---
@app.middleware("http")
async def ensure_utf8_encoding(request: Request, call_next):
    """This middleware ensures all responses have the correct UTF-8 charset."""
    response = await call_next(request)
    if "charset" not in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response
# -----------------------------------------------

# CORS Middleware should come after your custom middleware
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
