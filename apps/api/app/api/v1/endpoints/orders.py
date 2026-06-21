# apps/api/app/api/v1/endpoints/orders.py

from fastapi import APIRouter, Depends, Query
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app import schemas, models
from app.api import deps


router = APIRouter()


@router.get("/me", response_model=schemas.PaginatedOrders)
async def read_my_orders(
    *,
    session: AsyncSession = Depends(deps.get_async_session),
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
