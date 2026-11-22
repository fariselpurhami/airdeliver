# apps/api/app/models/enums.py

from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    OPERATOR = "operator"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
    SAVED_FOR_LATER = "saved_for_later"



class NotificationType(str, Enum):
    ORDER_UPDATE = "order_update"
    SYSTEM_ALERT = "system_alert"
    SECURITY = "security"
    PROMOTION = "promotion"


class CancellationReason(str, Enum):
    PRICE = "price"
    PAYMENT_METHOD = "payment_method"
    SHIPPING = "shipping"
    CHANGED_MIND = "changed_mind"
    OTHER = "other"
