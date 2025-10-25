from .ai_ordering import ChatRequest, ChatResponse, ResponseMessage
from .msg import Msg
from .token import Token, TokenData
from .audit_trail import AuditTrail
from .user import User, UserCreate, UserUpdate, UserRead # Added UserRead for consistency
from .product import Product, ProductCreate, ProductUpdate, ProductRead # Added ProductRead
from .drone import Drone 

# Import the correct schemas from order.py
from .order import Order, OrderCreate, OrderUpdate, OrderItemRead, OrderItemCreate, OrderRead, PaginatedOrders # Use OrderItemRead, add OrderRead, PaginatedOrders

from .payment import PaymentIntent

__all__ = [
    "Msg",
    "Token",
    "TokenData",
    "PaymentIntent",
    "AuditTrail",
    
    "User",
    "UserCreate",
    "UserUpdate",
    "UserRead", # Added UserRead
    
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "ProductRead", # Added ProductRead
    
    "Drone",
    
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "OrderRead", # Added OrderRead
    "PaginatedOrders", # Added PaginatedOrders
    
    "OrderItemRead", # Changed from OrderItem
    "OrderItemCreate",
]
