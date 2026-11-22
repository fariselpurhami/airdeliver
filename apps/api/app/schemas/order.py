from datetime import datetime
from typing import List, Optional

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel

from app.models.order import OrderStatus
from app.schemas.product import ProductRead
from app.schemas.user import UserRead

class OrderItemBase(SQLModel):
    product_id: int
    quantity: int = Field(gt=0)

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemRead(OrderItemBase):
    id: int
    price_per_unit: float
    product: Optional[ProductRead] = None
    model_config = ConfigDict(from_attributes=True)

class OrderBase(SQLModel):
    pass

class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = Field(min_length=1)

class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = None

class OrderRead(OrderBase):
    id: int
    user_id: int
    status: OrderStatus
    total_price: float
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemRead] = []
    model_config = ConfigDict(from_attributes=True)

class PaginatedOrders(SQLModel):
    total: int
    page: int
    limit: int
    orders: List[OrderRead]

class Order(OrderRead):
    user: Optional[UserRead] = None
