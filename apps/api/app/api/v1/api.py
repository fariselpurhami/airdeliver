# apps/api/app/api/v1/api.py 

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
    health
)
api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(products.router, prefix="/products", tags=["Products"]) 
api_router.include_router(ai_support.router, prefix="/ai-support", tags=["AI Neural Core"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(ai_ordering.router, prefix="/ai-ordering", tags=["AI Ordering"])
api_router.include_router(users.router, prefix="/users", tags=["Users"]) 
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])

from .endpoints import customer_memory
api_router.include_router(customer_memory.router, prefix="/users/me", tags=["Customer Memory"])

from .endpoints import password_reset
api_router.include_router(password_reset.router, prefix='/auth', tags=['Authentication'])
