# apps/api/app/api/v1/endpoints/orders.py

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app import models, schemas
from app.api import deps

# Configure module-level logger for structured observability
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/me",
    response_model=schemas.PaginatedOrders,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user's orders",
    description="Fetches a paginated list of orders for the authenticated user, ordered by creation date descending.",
)
async def read_my_orders(
    *,
    response: Response,
    session: AsyncSession = Depends(deps.get_async_session),
    current_user: models.User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    limit: int = Query(10, ge=1, le=100, description="Items per page, bounded to prevent unbounded memory allocation"),
) -> schemas.PaginatedOrders:
    """
    Retrieve paginated orders for the authenticated user.
    Enforces strict access boundaries, protects against unoptimized queries,
    and isolates database errors from client-facing responses.
    """
    response.headers["Cache-Control"] = "no-store"
    offset = (page - 1) * limit

    try:
        # 1. Determine total count of user's orders
        count_statement = select(func.count(models.Order.id)).where(
            models.Order.user_id == current_user.id
        )
        
        total_count_result = await session.execute(count_statement)
        total_count = total_count_result.scalar_one()

        # 2. Fast-path exit: avoid unnecessary database joins and query execution if no records exist
        if total_count == 0:
            return schemas.PaginatedOrders(
                total=0,
                orders=[],
                page=page,
                limit=limit
            )

        # 3. Retrieve paginated result set with eager loading to prevent N+1 query performance degradation
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

        orders_result = await session.execute(orders_statement)
        # Use .scalars().all() to extract model instances from SQLAlchemy Row objects
        orders = list(orders_result.scalars().all())

        return schemas.PaginatedOrders(
            total=total_count,
            orders=orders,
            page=page,
            limit=limit
        )

    except SQLAlchemyError as e:
        # Log deep operational context for observability while stripping PII/Secrets
        logger.error(
            "Database operation failed during read_my_orders execution",
            extra={
                "user_id": current_user.id,
                "page": page,
                "limit": limit,
                "error_details": str(e),
            },
            exc_info=True
        )
        # Enforce secure error boundary: Never leak infrastructure internals to the caller
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal infrastructure error occurred while processing your request.",
        ) from None

    except Exception as e:
        # Catch-all for unexpected runtime anomalies to guarantee graceful degradation
        logger.error(
            "Unexpected systemic failure in read_my_orders",
            extra={
                "user_id": current_user.id,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected system error occurred.",
        ) from None


@router.get("/me/{order_id}", response_model=schemas.OrderRead)
async def read_my_order(
    response: Response,
    order_id: int = Path(gt=0, le=2147483647),
    session: AsyncSession = Depends(deps.get_async_session),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> schemas.OrderRead:
    """Lookup an owned order directly, never infer absence from a history page.

    Missing and other customers' orders share a404 response. No address,
    payment identifier or internal checkout payload is exposed by OrderRead.
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        result = await session.execute(
            select(models.Order)
            .where(models.Order.id == order_id, models.Order.user_id == current_user.id)
            .options(selectinload(models.Order.items).selectinload(models.OrderItem.product))
        )
        order = result.scalars().one_or_none()
    except SQLAlchemyError as exc:
        logger.error("Order detail read failed", extra={"user_id":current_user.id,"error_type":type(exc).__name__})
        raise HTTPException(status_code=503, detail="Order details are temporarily unavailable. Please try again.") from None
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found in your account.")
    return order
