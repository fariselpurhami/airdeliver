# apps/api/app/api/v1/endpoints/health.py

from fastapi import APIRouter, Depends, status, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from app.db.session import get_session
from app.services.cache_service import IAsyncCacheClient, get_cache_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_session),
    cache: IAsyncCacheClient = Depends(get_cache_client),
):
    status_data = {
        "status": "ok",
        "database": "unknown",
        "redis": "disabled"
    }

    try:
        await db.exec(text("SELECT 1"))
        status_data["database"] = "connected"
    except Exception as e:
        logger.error(f"DB Health Fail: {e}")
        status_data["database"] = "disconnected"
        status_data["status"] = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    if settings.USE_REDIS:
        try:
            is_connected = await cache.ping()
            if is_connected:
                status_data["redis"] = "connected"
            else:
                logger.error("Health Check: Redis Ping Failed (check connection params)")
                status_data["redis"] = "disconnected"
                status_data["status"] = "error"
                response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        except Exception as e:
            logger.error(f"Health Check Redis Exception: {e}")
            status_data["redis"] = "error"
            status_data["status"] = "error"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return status_data
