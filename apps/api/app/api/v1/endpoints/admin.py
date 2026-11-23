# apps/api/app/api/v1/endpoints/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict, field_validator
import random
from app.api import deps
from app import models
from app.models.enums import OrderStatus

router = APIRouter()


class AdminStatsResponse(BaseModel):
    total_revenue: float
    total_orders: int
    total_products: int
    pending_deliveries: int
    active_users_today: int


class AdminOrder(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: float
    currency: str
    is_paid: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAdminOrdersResponse(BaseModel):
    total_orders: int
    orders: List[AdminOrder]


def get_current_admin_user(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> models.User:
    if not current_user.role or current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. You do not have permission to view this page.",
        )
    return current_user


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    dependencies=[Depends(get_current_admin_user)],
)
async def get_admin_stats(db: AsyncSession = Depends(deps.get_async_session)):
    total_revenue = (
        await db.execute(
            select(func.sum(models.Order.total_price)).where(
                models.Order.status.in_([OrderStatus.DELIVERED, OrderStatus.IN_TRANSIT])
            )
        )
    ).scalar() or 0.0

    total_orders = (await db.execute(select(func.count(models.Order.id)))).scalar() or 0
    total_products = (await db.execute(select(func.count(models.Product.id)))).scalar() or 0
    pending_deliveries = (
        await db.execute(
            select(func.count(models.Order.id)).where(
                models.Order.status == OrderStatus.PROCESSING
            )
        )
    ).scalar() or 0

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    active_users_today = (
        await db.execute(
            select(func.count(func.distinct(models.Order.user_id))).where(
                models.Order.created_at >= today_start
            )
        )
    ).scalar() or 0

    return AdminStatsResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_products=total_products,
        pending_deliveries=pending_deliveries,
        active_users_today=active_users_today,
    )


@router.get(
    "/orders",
    response_model=PaginatedAdminOrdersResponse,
    dependencies=[Depends(get_current_admin_user)],
)
async def get_admin_orders(
    db: AsyncSession = Depends(deps.get_async_session),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
):
    offset = (page - 1) * limit
    total_orders = (await db.execute(select(func.count(models.Order.id)))).scalar_one() or 0

    orders_query = (
        select(models.Order)
        .order_by(models.Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = (await db.execute(orders_query)).scalars().all()

    return PaginatedAdminOrdersResponse(total_orders=total_orders, orders=orders)


class FulfillmentTransition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    from_status: OrderStatus
    to_status: OrderStatus
    evidence: str

    @field_validator('evidence')
    @classmethod
    def evidence_required(cls,value):
        value=' '.join(value.split())
        if len(value)<10 or len(value)>500:
            raise ValueError('Provide10..500characters of operator evidence, no secrets')
        return value


@router.post('/orders/{order_id}/fulfillment')
async def update_manual_fulfillment(
    order_id: int,
    payload: FulfillmentTransition,
    response: Response,
    db: AsyncSession = Depends(deps.get_async_session),
    admin: models.User = Depends(get_current_admin_user),
):
    """Manual operator attestation, not a carrier scan or automatic delivery.

    Atomic audit+in-app notification with guarded transitions. No notification
    email/push, no provider, no refund or payment-state writes.
    """
    from app.models.audit_trail import AuditTrail
    from app.models.notification import Notification
    from app.models.enums import NotificationType
    from sqlalchemy.exc import SQLAlchemyError
    if order_id<1 or order_id>2147483647:
        raise HTTPException(status_code=422,detail='Invalid order identifier')
    transitions={OrderStatus.PROCESSING:OrderStatus.ASSIGNED,OrderStatus.ASSIGNED:OrderStatus.IN_TRANSIT,OrderStatus.IN_TRANSIT:OrderStatus.DELIVERED}
    response.headers['Cache-Control']='no-store'
    try:
        order=await db.get(models.Order,order_id,with_for_update=True,populate_existing=True)
        if order is None:raise HTTPException(status_code=404,detail='Order not found')
        if not order.is_paid:raise HTTPException(status_code=409,detail='Only confirmed paid orders can enter fulfillment')
        # Retry is harmless only for the exact same operation evidence. An old
        # retry cannot rewind a newer status or impersonate another operator.
        description=f'Manual fulfillment {payload.from_status.value}->{payload.to_status.value}: {payload.evidence}'
        if order.status==payload.to_status:
            prior=(await db.execute(select(AuditTrail).where(AuditTrail.order_id==order.id,AuditTrail.changed_by==admin.id,AuditTrail.event_description==description))).scalars().first()
            if prior:
                await db.commit()
                return {'status':order.status,'order_id':order.id,'source':'manual_operator','replayed':True}
        if order.status!=payload.from_status or transitions.get(order.status)!=payload.to_status:
            raise HTTPException(status_code=409,detail='Order changed or transition not allowed. Refresh before continuing.')
        order.status=payload.to_status
        db.add(order)
        db.add(AuditTrail(order_id=order.id,changed_by=admin.id,event_description=description))
        labels={OrderStatus.ASSIGNED:'Assigned for fulfillment',OrderStatus.IN_TRANSIT:'Marked in transit',OrderStatus.DELIVERED:'Marked delivered'}
        db.add(Notification(user_id=order.user_id,related_order_id=order.id,title=labels[order.status],
            body=f'An authorized store operator updated order #{order.id}. This is a manual store record, not an automated carrier scan.',
            type=NotificationType.ORDER_UPDATE,meta={'cta':f'/tracking/{order.id}','source':'manual_operator'}))
        await db.commit()
        return {'status':order.status,'order_id':order.id,'source':'manual_operator','replayed':False}
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=503,detail='Fulfillment update could not be confirmed. Refresh the order before retrying.') from None
