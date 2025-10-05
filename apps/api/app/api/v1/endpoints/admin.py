# file: apps/api/app/api/v1/endpoints/admin.py
# version: 1.0.0
# date: 2025-09-30
# author: Gemini

from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List, Any

from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.models.product import Product
from app.models.order import Order

router = APIRouter()

# This entire router is protected, only admins can access it.
@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Any:
    """
    Get high-level statistics for the admin dashboard.
    """
    total_products = db.exec(select(Product)).all()
    total_orders = db.exec(select(Order)).all()
    
    # In a real app, revenue would be calculated from successful orders.
    # This is a placeholder calculation.
    total_revenue = sum(order.total_price for order in total_orders)
    
    return {
        "total_revenue": total_revenue,
        "total_orders": len(total_orders),
        "total_products": len(total_products),
        "active_drones": 0 # Placeholder, would come from drone service
    }

@router.get("/orders", response_model=List[Order])
def get_all_orders(
    db: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Get a list of all orders in the system.
    """
    orders = db.exec(select(Order).order_by(Order.created_at.desc())).all()
    return orders
