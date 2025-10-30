# apps/api/api/schemas/order.py  

from sqlmodel import SQLModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus
from app.schemas.product import ProductRead 
from app.schemas.user import UserRead 

class OrderItemBase(SQLModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemRead(OrderItemBase):
    id: int 
    price_per_unit: float
    product: Optional[ProductRead] = None 

    model_config = { "from_attributes": True }

class OrderBase(SQLModel):
    pass

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = None
    drone_id: Optional[int] = None

class OrderRead(OrderBase):
    id: int
    user_id: int 
    status: OrderStatus
    total_price: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead] = []
    drone_id: Optional[int] = None

    model_config = { "from_attributes": True }

class PaginatedOrders(SQLModel):
    total: int
    page: int
    limit: int
    orders: List[OrderRead]

class Order(OrderRead):
    
     user: Optional[UserRead] = None 
     
