# file: apps/api/app/main.py

import logging
from app.db import base 
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from app.db.session import engine
from starlette.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.websockets.tracking_ws import router as tracking_router
from app.core.limiter import limiter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address 
from slowapi.errors import RateLimitExceeded


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI(
    title="airdeliver API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    This catches any exception that is not handled by a more specific handler.
    """
    
    logging.error(f"Global exception handler caught: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"message": f"An unexpected server error occurred. Please check the logs."},
    )
# ------------------------------------------------

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.middleware("http")
async def ensure_utf8_encoding(request: Request, call_next):
    """This middleware ensures all responses have the correct UTF-8 charset."""
    response = await call_next(request)
    if "charset" not in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(tracking_router, prefix="/ws")

@app.get("/")
def read_root():
    return {"message": "Welcome to airdeliver API"}
