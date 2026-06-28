# apps/api/app/api/v1/endpoints/ai_support.py

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
        min_length=1,
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
) -> NeuralCoreResponse:
    
    # 1. Context Extraction & Telemetry
    # Extract distributed tracing/correlation ID from middleware or generate a localized one.
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    user_id = current_user.id if current_user else None
    
    # Cleanse inputs at the boundary
    clean_message = payload.message.strip()
    
    logger.info(
        "Initiating Neural Core processing",
        extra={
            "correlation_id": correlation_id,
            "session_id": payload.session_id,
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
                "session_id": payload.session_id,
                "user_id": user_id,
                "error_type": error_type,
                "error_message": str(e),
            },
            exc_info=True,
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
