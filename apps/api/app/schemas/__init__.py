# In your schemas/__init__.py or models/__init__.py file

# Base schemas/models that don't have complex relationships
from .msg import Msg
from .token import Token, TokenData
from .audit_trail import AuditTrail
# Core data models
from .user import User, UserCreate, UserUpdate
from .product import Product, ProductCreate, ProductUpdate
from .drone import Drone # You were missing this import

# Dependent models (Order depends on User, Product, and Drone)
from .order import Order, OrderCreate, OrderUpdate, OrderItem, OrderItemCreate

# Utility/other schemas
from .payment import PaymentIntent

# The __all__ list should include everything you want to export
__all__ = [
    # Base
    "Msg",
    "Token",
    "TokenData",
    "PaymentIntent",
    "AuditTrail",
    
    # Core Models & Schemas
    "User",
    "UserCreate",
    "UserUpdate",
    "Product",
    "ProductCreate",
    "ProductUpdate",
    "Drone",
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "OrderItem",
    "OrderItemCreate",
]
