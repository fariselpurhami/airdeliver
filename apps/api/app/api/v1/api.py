# In airdeliver/apps/api/app/api/v1/api.py

from fastapi import APIRouter

# استيراد واحد ومنظم لجميع الـ endpoints
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
    tools
)

api_router = APIRouter()

# --- تضمين الرواترز بالترتيب المنطقي ---
# الرواترز الأساسية أولاً
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])

# الرواترز التي تعتمد على غيرها (مثل الطلبات) تكون في الآخر
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(tools.router, prefix="/tools", tags=["AI Tools"])
api_router.include_router(ai_support.router, prefix="/ai-support", tags=["AI Neural Core"])
# بقية الرواترز
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(ai_ordering.router, prefix="/ai-ordering", tags=["AI Ordering"])
