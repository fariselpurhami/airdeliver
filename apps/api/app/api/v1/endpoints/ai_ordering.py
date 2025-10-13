# file: apps/api/app/api/v1/endpoints/ai_ordering.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.api import deps
from app import models, schemas
from app.db.session import get_session
from app.services.ai_ordering_service import ai_ordering_service

router = APIRouter()

@router.post("/chat", response_model=schemas.ChatResponse)
def handle_chat_message(
    *,
    db: Session = Depends(get_session),
    request: schemas.ChatRequest,
    # NOTE: The strict login dependency below is commented out for easier development.
    # In production, you would remove the temporary block below and re-enable this line.
    # current_user: models.User = Depends(deps.get_current_active_user), 
):
    """
    Main endpoint for the AI Ordering Agent.
    """
    
    # --- TEMPORARY BLOCK FOR DEVELOPMENT ---
    # This automatically gets the first user from the database to avoid 401 errors.
    first_user = db.exec(select(models.User)).first()
    if not first_user:
        raise HTTPException(
            status_code=404, 
            detail="No users found in the database. Please create or seed a user first."
        )
    current_user = first_user
    # --- END OF TEMPORARY BLOCK ---

    # The user object is now passed to the service
    responses = ai_ordering_service.handle_message(db, request.message, user=current_user)
    return {"responses": responses}
