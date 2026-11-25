#  backend/api/app/api/v1/endpoints/health.py

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response, status
from app.api.deps import get_current_admin_user
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import CoreSettings, get_core_settings
from app.services.ai_commerce_engine import model_registry
from app.db.session import get_async_session
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


ComponentStatus = Literal["connected", "disconnected", "disabled", "error"]
OverallStatus = Literal["ok", "error"]


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    response: Response,
    settings: CoreSettings = Depends(get_core_settings),
    db: AsyncSession = Depends(get_async_session),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
) -> dict[str, str]:
    overall_status: OverallStatus = "ok"
    database_status: ComponentStatus = "unknown"  # type: ignore[assignment]
    redis_status: ComponentStatus = "disabled"

    try:
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        logger.error('Database readiness check failed.')
        database_status = "disconnected"
        overall_status = "error"

    if settings.USE_REDIS:
        try:
            redis_reachable = await cache.ping()
            if redis_reachable:
                redis_status = "connected"
            else:
                redis_status = "disconnected"
                overall_status = "error"
                logger.error("Redis readiness check returned an unhealthy ping result.")
        except Exception:
            logger.error('Redis readiness check failed.')
            redis_status = "error"
            overall_status = "error"

    text_status = model_registry.text_readiness()["state"]
    if text_status != "ready":
        overall_status = "error"

    if overall_status == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "database": database_status,
        "redis": redis_status,
        "text_embeddings": text_status,
    }


@router.get("/health/behavior")
async def behavior_model_health(request: Request, current_admin=Depends(get_current_admin_user)) -> dict:
    engine = getattr(request.app.state, "behavior", None)
    if engine is None:
        return {"state": "unavailable", "inference_ready": False, "production_approved": False}
    return engine.model_status()
