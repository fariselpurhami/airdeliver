# file: apps/api/app/api/v1/endpoints/admin.py

from fastapi import APIRouter, Depends, Query 
from sqlmodel import Session, select, func 
from typing import List, Any
from pydantic import BaseModel 

from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.models.product import Product
from app.models.order import Order 

router = APIRouter()

# --- schema Pagination ---

class OrdersPage(BaseModel):
    orders: List[Order]
    total_orders: int

# --- Endpoint ---
@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Any:
    """
    Get high-level statistics for the admin dashboard.
    """

    total_products_count = db.exec(select(func.count(Product.id))).one()
    total_orders_count = db.exec(select(func.count(Order.id))).one()

    
    orders_for_revenue = db.exec(select(Order.total_price)).all()
    total_revenue = sum(price for price in orders_for_revenue if price is not None)

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders_count,
        "total_products": total_products_count,
        "active_drones": 0 # Placeholder
    }


# --- Endpoint Pagination ---
@router.get("/orders", response_model=OrdersPage) # <-- response_model
def read_orders_paginated( 
    *,
    db: Session = Depends(get_session),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    current_user: User = Depends(deps.get_current_admin_user) 
):
    """
    Retrieve orders with pagination. (Admin only)
    """

    offset = (page - 1) * limit

    
    statement = select(Order).order_by(Order.created_at.desc()).offset(offset).limit(limit)
    orders_on_page = db.exec(statement).all()

    
    count_statement = select(func.count()).select_from(Order)
    total_orders = db.exec(count_statement).one()

    
    return {"orders": orders_on_page, "total_orders": total_orders}
