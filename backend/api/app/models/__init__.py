# backend/api/app/models/__init__.py

from .enums import (
    UserRole,
    OrderStatus,
    NotificationType,
    CancellationReason, # Added this
)

from .audit_trail import AuditTrail
from .gamification import Badge, UserBadge, UserActivity # Added UserActivity
from .notification_subscription import NotificationSubscription
from .notification import Notification
from .order import Order, OrderItem 
from .product import Product
from .user import User
from .payment_outbox import PaymentOutbox
from .aimemory import AIMemory 

__all__ = [
    "UserRole",
    "OrderStatus",
    "NotificationType",
    "CancellationReason",
    "AuditTrail",
    "Badge",
    "UserBadge",
    "UserActivity",
    "NotificationSubscription",
    "Notification",
    "Order",
    "OrderItem",
    "Product",
    "User",
    "AIMemory",
    "PaymentOutbox",
]

from app.models.customer_memory import CustomerMemoryConsent, CustomerShoppingMemory
from app.models.cart_journal import CustomerCartState, CartMutationRecord
