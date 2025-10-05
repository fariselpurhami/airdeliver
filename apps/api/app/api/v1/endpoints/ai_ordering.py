# file: apps/api/app/api/v1/endpoints/ai_ordering.py
# version: 1.0.0
# date: 2025-09-27
# author: Gemini

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.ai_ordering import ChatRequest, ChatResponse
from app.services.ai_ordering_service import ai_ordering_service

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat_message(
    *,
    db: Session = Depends(get_session),
    request: ChatRequest,
):
    """
    Main endpoint for the AI Ordering Agent.
    Receives a user message and returns the AI's response.
    """
    responses = ai_ordering_service.handle_message(db, request.message)
    return {"responses": responses}
