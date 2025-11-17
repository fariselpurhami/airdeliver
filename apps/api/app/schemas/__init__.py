# apps/api/app/schemas/__init__.py

from .ai_ordering import ChatRequest, ChatResponse, ResponseMessage
from .msg import Msg
from .token import Token, TokenData, TokenPayload
from .audit_trail import AuditTrail
from .user import User, UserCreate, UserUpdate, UserRead 
from .product import Product, ProductCreate, ProductUpdate, ProductRead 
from .drone import DroneRead, DroneCreate, DroneUpdate
from .order import Order, OrderCreate, OrderUpdate, OrderItemRead, OrderItemCreate, OrderRead, PaginatedOrders 
from .payment import PaymentIntent
from .notification import NotificationRead

__all__ = [
    "Msg",
    "Token",
    "TokenData",
    "TokenPayload",
    "PaymentIntent",
    "AuditTrail",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserRead", 
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "ProductRead",
    "DroneRead", 
    "DroneCreate", 
    "DroneUpdate",
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "OrderRead", 
    "PaginatedOrders", 
    "OrderItemRead", 
    "OrderItemCreate",
    "NotificationRead",
]
