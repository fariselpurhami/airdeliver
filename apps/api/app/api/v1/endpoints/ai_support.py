# apps/api/app/api/v1/endpoints/ai_support.py

import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel
from typing import Optional

from app.api import deps
from app import models
from app.db.session import get_session
from app.services.neural_core_service import NeuralCoreService, get_neural_core_service
from app.schemas.ai_actions import NeuralCoreResponse

router = APIRouter()
logger = logging.getLogger(__name__)

class SupportRequest(SQLModel):
    message: str
    session_id: str

@router.post("/chat", response_model=NeuralCoreResponse)
async def handle_support_chat(
    *,
    db: AsyncSession = Depends(get_session),
    request_data: SupportRequest = Body(...),
    current_user: Optional[models.User] = Depends(deps.get_optional_current_user),
    neural_service: NeuralCoreService = Depends(get_neural_core_service),
):
    
    if not request_data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    if not request_data.session_id.strip():
        raise HTTPException(status_code=400, detail="Session ID is required.")

    try:
        response_envelope = await neural_service.handle_message(
            db=db,
            message=request_data.message,
            user=current_user,
            session_id=request_data.session_id,
        )
        return response_envelope

    except Exception as e:
        logger.error(
            f"🔥 CRITICAL: Uncaught exception in Neural Core: {e}", exc_info=True
        )
        return NeuralCoreResponse(
            text="I'm currently optimizing my neural pathways. Please try again in a few seconds.",
            action=None,
            explain=f"System Exception: {str(e)}",
            confidence=0.0,
            telemetry={
                "intent": "SYSTEM_ERROR", 
                "error": str(e), 
                "entities": [] 
            },
        )
