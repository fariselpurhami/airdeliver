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

class DroneStatus(str, Enum):
    IDLE = "idle"
    CHARGING = "charging"
    PREPARING = "preparing" 
    READY = "ready"     
    IN_MISSION = "in_mission" 
    RETURNING = "returning"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline" 

class MissionStatus(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    PREFLIGHT_CHECKS = "preflight_checks"
    ARMED = "armed"
    TAKEOFF = "takeoff"
    IN_TRANSIT = "in_transit"
    APPROACH = "approach"
    DROPPING = "dropping"
    RETURNING = "returning"
    LANDING = "landing"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED_PREFLIGHT = "failed_preflight"
    FAILED_COMMS_TIMEOUT = "failed_comms_timeout"
    FAILED_LOW_BATTERY = "failed_low_battery"
    FAILED_GPS_LOSS = "failed_gps_loss"
    FAILED_PAYLOAD = "failed_payload"
    FAILED_HARDWARE = "failed_hardware"
    FAILED_EMERGENCY_LANDING = "failed_emergency_landing"

class NotificationType(str, Enum):
    ORDER_UPDATE = "order_update" 
    DRONE_STATUS = "drone_status" 
    SYSTEM_ALERT = "system_alert" 
    SECURITY = "security"
    PROMOTION = "promotion"

class EventType(str, Enum):
    PREFLIGHT_OK = "preflight_ok"
    PREFLIGHT_FAILED = "preflight_failed"
    ARMED = "armed"
    TAKEOFF = "takeoff"
    PAYLOAD_DROPPED = "payload_dropped"
    LANDED = "landed"
    MISSION_COMPLETED = "mission_completed"
    EMERGENCY_LANDING = "emergency_landing"
