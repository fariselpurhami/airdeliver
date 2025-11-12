# apps/api/app/api/v1/endpoints/orders.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from sqlalchemy.orm import selectinload
from app import schemas, models
from app.models.product import Product
from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.services.payment_orchestrator import payment_orchestrator

router = APIRouter()


@router.post("/create-payment-intent", response_model=schemas.PaymentIntent)
async def create_payment_intent(
    *,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    items: List[schemas.OrderItemCreate],
):
    if not items:
        raise HTTPException(
            status_code=400, detail="Cannot create payment for an empty cart."
        )

    total_price = 0.0
    for item in items:
        product = await session.get(Product, item.product_id)
        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product with id {item.product_id} not found"
            )
        total_price += float(product.price) * item.quantity

    payment_info = payment_orchestrator.process_payment(
        amount=total_price, currency="usd", region="US"
    )

    if "error" in payment_info or not payment_info.get("clientSecret"):
        raise HTTPException(
            status_code=500,
            detail=payment_info.get(
                "error", "Failed to create payment intent with the provider."
            ),
        )

    return payment_info


@router.get("/me", response_model=schemas.PaginatedOrders)
async def read_my_orders(
    *,
    session: AsyncSession = Depends(deps.get_session),
    current_user: models.User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    offset = (page - 1) * limit

    count_statement = select(func.count(models.Order.id)).where(
        models.Order.user_id == current_user.id
    )
    total_count = (await session.exec(count_statement)).one_or_none() or 0

    orders_statement = (
        select(models.Order)
        .where(models.Order.user_id == current_user.id)
        .options(
            selectinload(models.Order.items).selectinload(models.OrderItem.product),
            selectinload(models.Order.user),
        )
        .order_by(models.Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = (await session.exec(orders_statement)).all()

    return schemas.PaginatedOrders(
        total=total_count, orders=orders, page=page, limit=limit
    )
