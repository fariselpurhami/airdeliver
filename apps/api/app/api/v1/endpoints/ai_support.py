# file: apps/api/app/api/v1/endpoints/ai_support.py

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
    # The strict login dependency below is commented out for easier development.
    # current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    The new, intelligent endpoint for the airdeliver Neural Core.
    """
    
    # TEMPORARY BLOCK FOR DEVELOPMENT: Automatically use the first user
    first_user = db.exec(select(models.User)).first()
    if not first_user:
        raise HTTPException(
            status_code=404, 
            detail="No users found in database. Please run seed.py."
        )
    current_user = first_user
    # END OF TEMPORARY BLOCK

    response_envelope = neural_core_service.handle_message(
        db=db,
        message=request.message,
        user=current_user
    )
    return response_envelope
