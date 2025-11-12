# apps/api/app/db/base.py

from app.db.base_class import Base  
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.drone import Drone
from app.models.mission import Mission
from app.models.audit_trail import DroneTelemetry, DroneEvent, AuditTrail
from app.models.ai_cart import AIOrderingCartItem
from app.models.notification import Notification
from app.models.notification_subscription import NotificationSubscription
from app.models.aimemory import AIMemory
from app.models.gamification import UserActivity, Badge, UserBadge

# تم إزالة الوسيط الخاطئ: update_forward_refs=True

User.model_rebuild()
Product.model_rebuild()
Order.model_rebuild()
OrderItem.model_rebuild()
Drone.model_rebuild()
Mission.model_rebuild()
DroneTelemetry.model_rebuild()
DroneEvent.model_rebuild()
AuditTrail.model_rebuild()
AIOrderingCartItem.model_rebuild()
Notification.model_rebuild()
NotificationSubscription.model_rebuild()
AIMemory.model_rebuild()
UserActivity.model_rebuild()
Badge.model_rebuild()
UserBadge.model_rebuild()
