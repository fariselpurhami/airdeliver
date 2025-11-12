from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api import deps
from app import models, schemas
from app.db.session import get_session
from app.services.ai_ordering_service import ai_ordering_service

router = APIRouter()


@router.post("/chat", response_model=schemas.ChatResponse)
async def handle_chat_message(
    *,
    db: AsyncSession = Depends(get_session),
    request: schemas.ChatRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    responses = await ai_ordering_service.handle_message(
        db, request.message, user=current_user
    )

    return {"responses": responses}
