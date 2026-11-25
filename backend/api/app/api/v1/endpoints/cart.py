# backend/api/app/api/v1/endpoints/cart.py

from fastapi import APIRouter, Depends
from app.api import deps
from app.crud import crud_cart
from app.schemas import Cart, CartItemCreate
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user import User


router = APIRouter()


@router.get("/", response_model=Cart)
async def get_cart(
    db: AsyncSession = Depends(deps.get_async_session),
    user: User = Depends(deps.get_current_user),
):
    """Retrieve the current user's cart."""
    return await crud_cart.get_or_create(db=db, user_id=user.id)


@router.post("/add", response_model=Cart)
async def add_to_cart(
    item: CartItemCreate,
    db: AsyncSession = Depends(deps.get_async_session),
    user: User = Depends(deps.get_current_user),
):
    """Add an item to the current user's cart."""
    return await crud_cart.add_item(db=db, user_id=user.id, item=item)
