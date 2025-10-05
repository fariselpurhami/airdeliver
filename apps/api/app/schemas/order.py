# file: apps/api/app/schemas/order.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini 2.5 Pro

from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus
from app.schemas.product import Product
from app.schemas.user import User

class OrderItemBase(SQLModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    price_per_unit: float
    product: Product

    class Config:
        from_attributes = True

class OrderBase(SQLModel):
    pass

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = None
    drone_id: Optional[int] = None

class Order(OrderBase):
    id: int
    user: User
    status: OrderStatus
    total_price: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]
    drone_id: Optional[int] = None

    class Config:
        from_attributes = True
