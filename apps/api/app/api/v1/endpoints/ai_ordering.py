# apps/api/app/api/v1/endpoints/ai_ordering.py

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

@router.patch("/order/{order_id}/cancel", response_model=models.Order)
async def cancel_order(
    *,
    db: AsyncSession = Depends(get_session),
    order_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    try:
        order = await ai_ordering_service.cancel_order_by_id(
            db=db, order_id=order_id, user_id=current_user.id
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found or you do not have permission to cancel it.",
            )

        return order

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
