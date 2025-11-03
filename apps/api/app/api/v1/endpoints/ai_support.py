# apps/api/app/api/v1/endpoints/ai_support.py

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.services.neural_core_service import neural_core_service
from app.schemas.ai_actions import NeuralCoreResponse
from app.schemas.ai_ordering import ChatRequest
from app.api import deps
from app import models

router = APIRouter()

@router.post("/chat", response_model=NeuralCoreResponse)
def handle_neural_core_chat(
    request: ChatRequest,
    db: Session = Depends(deps.get_session),
    current_user: models.User = Depends(deps.get_current_active_user),
):

    try:
       response_envelope = neural_core_service.handle_message(
           db=db,
           message=request.message,
           user=current_user
       )
       return response_envelope

    except Exception as e:
        logging.error(f"An uncaught exception occurred in the chat endpoint: {e}", exc_info=True)
        
        raise HTTPException(status_code=500, detail="An internal error occurred in the Neural Core.")
