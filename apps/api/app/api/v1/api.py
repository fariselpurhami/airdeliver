# In airdeliver/apps/api/app/api/v1/api.py

from fastapi import APIRouter

from .endpoints import (
    admin,
    auth,
    users,
    products,
    orders,
    notifications,
    webhooks,
    ai_ordering,
    ai_support,
    tools,
    drones
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(drones.router, prefix="/drones", tags=["Drones"])

api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(tools.router, prefix="/tools", tags=["AI Tools"])
api_router.include_router(ai_support.router, prefix="/ai-support", tags=["AI Neural Core"])

api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(ai_ordering.router, prefix="/ai-ordering", tags=["AI Ordering"])
