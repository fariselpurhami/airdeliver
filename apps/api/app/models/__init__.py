# file: airdeliver/apps/api/app/models/__init__.py (Corrected)

# Import Enums first from the dedicated file
from .enums import (
    UserRole,
    OrderStatus,
    DroneStatus,
    MissionStatus,
    NotificationType,
    EventType,
)

# Import Models
from .audit_trail import AuditTrail
from .drone import Drone, DroneTelemetry, DroneEvent # Import all drone models
from .gamification import Badge, UserBadge
from .mission import Mission
from .notification_subscription import NotificationSubscription
from .notification import Notification
from .order import Order, OrderItem # Import both order models
from .product import Product
from .user import User
from .aimemory import AIMemory # Import from its own file

__all__ = [
    # Enums
    "UserRole",
    "OrderStatus",
    "DroneStatus",
    "MissionStatus",
    "NotificationType",
    "EventType",

    # Models
    "AuditTrail",
    "Drone",
    "DroneTelemetry",
    "DroneEvent",
    "Badge",
    "UserBadge",
    "Mission",
    "NotificationSubscription",
    "Notification",
    "Order",
    "OrderItem",
    "Product",
    "User",
    "AIMemory",
]
