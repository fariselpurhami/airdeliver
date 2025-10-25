from sqlmodel import SQLModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.order import OrderStatus
from app.schemas.product import ProductRead # Assuming ProductRead exists for API response
from app.schemas.user import UserRead # Assuming UserRead exists for API response

class OrderItemBase(SQLModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemRead(OrderItemBase):
    id: int # Assuming OrderItem model has an ID
    price_per_unit: float
    product: Optional[ProductRead] = None # Use ProductRead for API

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
    user_id: int # Keep user_id for simplicity or embed UserRead
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

# Existing Order schema if used elsewhere, ensure fields match OrderRead if needed
class Order(OrderRead):
     # You might include the full User object here if needed by other parts
     user: Optional[UserRead] = None 
     
