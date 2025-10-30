# apps/api/app/api/v1/endpoints/admin.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel
import random 
from app.api import deps
from app import models

router = APIRouter()

class AdminStatsResponse(BaseModel):
    total_revenue: float
    total_orders: int
    total_products: int
    active_drones: int
    pending_deliveries: int  
    active_users_today: int    

class AdminOrder(BaseModel):
    id: int
    user_id: int
    status: str
    total_price: float
    created_at: datetime

    class Config:
        from_attributes = True

class PaginatedAdminOrdersResponse(BaseModel):
    total_orders: int
    orders: List[AdminOrder]

def get_current_admin_user(
    current_user: models.User = Depends(deps.get_current_active_user)
) -> models.User:
    if not current_user.role or current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. You do not have permission to view this page."
        )
    return current_user

@router.get(
    "/stats", 
    response_model=AdminStatsResponse,
    dependencies=[Depends(get_current_admin_user)]
)
def get_admin_stats(
    db: Session = Depends(deps.get_session)
):
    
    total_revenue = db.exec(
        select(func.sum(models.Order.total_price))
        .where(models.Order.status.in_(["Delivered", "In Transit"]))
    ).first() or 0.0
    
    total_orders = db.exec(select(func.count(models.Order.id))).first() or 0
    total_products = db.exec(select(func.count(models.Product.id))).first() or 0
    active_drones = db.exec(
        select(func.count(models.Drone.id))
        .where(models.Drone.status.in_(["active", "idle", "charging"]))
    ).first() or 0
    
    pending_deliveries = db.exec(
        select(func.count(models.Order.id))
        .where(models.Order.status == "Processing") 
    ).first() or 0
    
    active_users_today = random.randint(50, 250) 
    
    return AdminStatsResponse(
        total_revenue=total_revenue,
        total_orders=total_orders,
        total_products=total_products,
        active_drones=active_drones,
        pending_deliveries=pending_deliveries,
        active_users_today=active_users_today    
    )

@router.get(
    "/orders", 
    response_model=PaginatedAdminOrdersResponse,
    dependencies=[Depends(get_current_admin_user)]
)
def get_admin_orders(
    db: Session = Depends(deps.get_session),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    offset = (page - 1) * limit
    total_orders = db.exec(select(func.count(models.Order.id))).first() or 0
    
    orders_query = (
        select(models.Order)
        .order_by(models.Order.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = db.exec(orders_query).all()
    
    return PaginatedAdminOrdersResponse(
        total_orders=total_orders,
        orders=orders
    )
