# backend/api/app/api/v1/endpoints/ai_support.py

import logging
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app import models
from app.api import deps
from app.db.session import get_async_session
from app.schemas.ai_actions import NeuralCoreResponse
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
from app.services.neural_core_service import NeuralCoreService, get_neural_core_service

# -----------------------------------------------------------------------------
# Configuration & Observability Setup
# -----------------------------------------------------------------------------
logger = logging.getLogger("airdeliver.api.support")

router = APIRouter()
# -----------------------------------------------------------------------------
# Dependency Injection (Modern FastAPI Annotated dependencies)
# -----------------------------------------------------------------------------
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
CurrentUserOptionalDep = Annotated[Optional[models.User], Depends(deps.get_optional_current_user)]
NeuralServiceDep = Annotated[NeuralCoreService, Depends(get_neural_core_service)]
CacheDep = Annotated[IAsyncCacheClient, Depends(get_cache_from_request)]

# -----------------------------------------------------------------------------
# Abuse Control (CWE-770): fixed-window per-client rate limiting.
# Mirrors the websocket chat policy (fail-open on cache failure).
# -----------------------------------------------------------------------------
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_MESSAGES = 30


async def check_support_rate_limit(client_key: str, cache: IAsyncCacheClient) -> bool:
    """Fixed-window counter. Returns True if allowed, False if the client
    exceeded RATE_LIMIT_MAX_MESSAGES inside RATE_LIMIT_WINDOW_SEC.
    Fails open when the cache is unavailable (same policy as the chat socket)."""
    key = f"support_ratelimit:{client_key}"
    try:
        current_count = await cache.incr(key)
        if current_count == 1:
            await cache.expire(key, RATE_LIMIT_WINDOW_SEC)
        if current_count > RATE_LIMIT_MAX_MESSAGES:
            logger.warning("support_chat.rate_limited", extra={"limit": RATE_LIMIT_MAX_MESSAGES})
            return False
        return True
    except Exception as exc:
        logger.warning("support_chat.rate_limit_fail_open", extra={"error_type": type(exc).__name__})
        return True

# -----------------------------------------------------------------------------
# Data Transfer Objects (DTO) / Schemas
# -----------------------------------------------------------------------------
class SupportRequestPayload(BaseModel):
    """
    Strict validation schema for incoming AI chat requests.
    Enforces security invariants: prevents oversized payloads (CWE-400) 
    and validates session ID format to prevent injection attacks (CWE-20).
    """
    message: str = Field(
        ...,
        min_length=0,
        max_length=4096,  # Hard bound on memory/token usage
        description="The user's message payload.",
        json_schema_extra={"example": "Where is my order?"}
    )
    session_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_-]+$",  # Restrict to safe, URL-friendly characters
        description="Idempotency and context tracking key."
    )
    image_base64: Optional[str] = Field(
        default=None,
        max_length=7_000_000,  # ~5MB binary ceiling; CWE-400 bound
        description=(
            "Optional base64-encoded image for visual product search. "
            "When present, the request is routed to visual similarity search "
            "and 'message' acts as an optional caption."
        ),
    )

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post(
    "/chat",
    response_model=NeuralCoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Process AI Support Chat via Neural Core",
    description=(
        "Ingests user dialogue, enforces rate/size limits, and delegates to the "
        "Neural Core Engine for semantic intent routing and response generation. "
        "Implements graceful degradation on upstream LLM or infrastructure failure."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Malformed request or validation failure"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid authentication credentials"},
    }
)
async def handle_support_chat(
    request: Request,
    payload: Annotated[SupportRequestPayload, Body(...)],
    db: DBSessionDep,
    current_user: CurrentUserOptionalDep,
    neural_service: NeuralServiceDep,
    cache: CacheDep,
) -> NeuralCoreResponse:

    # 1. Context Extraction & Telemetry
    # Extract distributed tracing/correlation ID from middleware or generate a localized one.
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    user_id = current_user.id if current_user else None

    # 1b. Abuse control: rate-limit per authenticated user, else per session.
    client_key = f"user:{user_id}" if user_id is not None else f"session:{payload.session_id}"
    if not await check_support_rate_limit(client_key, cache):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down and try again shortly.",
        )

    # Cleanse inputs at the boundary
    clean_message = payload.message.strip()
    if not clean_message and not payload.image_base64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide a message, an image, or both.",
        )
    
    logger.info(
        "Initiating Neural Core processing",
        extra={
            "correlation_id": correlation_id,
            "user_id": user_id,
            "message_length": len(clean_message),
        }
    )

    try:
        # 2. Domain Execution
        response_envelope = await neural_service.handle_message(
            db=db,
            message=clean_message,
            user=current_user,
            session_id=payload.session_id,
            image_base64=payload.image_base64,
        )
        
        # Inject correlation ID into successful telemetry for observability tracking
        response_envelope.enrich_telemetry(correlation_id=correlation_id)
        return response_envelope

    except Exception as e:
        # 3. Graceful Degradation & Incident Logging
        # Catch unexpected systemic failures (network partitions, LLM outages, DB timeouts).
        # We return a safely degraded 200 OK so the client UI doesn't crash, 
        # but we log as CRITICAL to trigger operational alerts.
        error_type = type(e).__name__
        
        logger.critical(
            "NEURAL_CORE_HARD_FAULT",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "error_type": error_type,
            },
        )

        return NeuralCoreResponse(
            text="My cognitive subsystems are currently recalibrating. Please try again in a moment.",
            action=None,
            explain="Graceful Degradation: Service Interruption",
            confidence=0.0,
            telemetry={
                "intent": "SYSTEM_DEGRADATION",
                "turn": 0,
                "user_id": user_id,
                "entities": [],
                "correlation_id": correlation_id,
                "fault_domain": error_type,
            }
        )

