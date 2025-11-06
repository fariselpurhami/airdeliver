import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, SQLModel
from app.api import deps
from app import models, schemas
from app.db.session import get_session
from app.services.neural_core_service import neural_core_service
from typing import Optional
from app.schemas.ai_actions import NeuralCoreResponse

router = APIRouter()

class SupportRequest(SQLModel):
    message: str
    session_id: str

@router.post("/chat", response_model=NeuralCoreResponse)
def handle_support_chat(
    *,
    db: Session = Depends(get_session),
    request_data: SupportRequest = Body(...),
    current_user: Optional[models.User] = Depends(deps.get_optional_current_user)
):
    if not request_data.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    if not request_data.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required.")

    try:
       response_envelope = neural_core_service.handle_message(
           db=db,
           message=request_data.message,
           user=current_user,
           session_id=request_data.session_id
       )
       return response_envelope

    except Exception as e:
        logging.error(f"An uncaught exception occurred in the chat endpoint: {e}", exc_info=True)
        return NeuralCoreResponse(
            text="I've encountered an unexpected server error. Please try again in a moment.",
            action=None,
            explain=f"Root exception: {str(e)}",
            confidence=1.0,
            telemetry={"intent": "CRITICAL_ERROR", "entities": [str(e)]}
        )
