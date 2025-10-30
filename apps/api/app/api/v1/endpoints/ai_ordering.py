# api/app/api/v1/endpoints/ai_ordering.py

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
):

    first_user = db.exec(select(models.User)).first()
    if not first_user:
        raise HTTPException(
            status_code=404, 
            detail="No users found in the database. Please create or seed a user first."
        )
    current_user = first_user
    responses = ai_ordering_service.handle_message(db, request.message, user=current_user)

    return {"responses": responses}
