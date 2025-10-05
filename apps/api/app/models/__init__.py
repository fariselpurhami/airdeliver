from .audit_trail import AuditTrail
from .drone import Drone, DroneStatus
from .gamification import Badge, UserBadge
from .notification_subscription import NotificationSubscription
from .order import Order, OrderItem, OrderStatus
from .product import Product
from .user import User, UserRole

# Manual rebuild to fix stubborn circular dependencies
AuditTrail.model_rebuild()
Drone.model_rebuild()
Badge.model_rebuild()
UserBadge.model_rebuild()
NotificationSubscription.model_rebuild()
Order.model_rebuild()
OrderItem.model_rebuild()
Product.model_rebuild()
User.model_rebuild()
