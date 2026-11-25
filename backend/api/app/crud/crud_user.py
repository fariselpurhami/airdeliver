# backend/api/app/crud/crud_user.py

from typing import Any, Dict, Optional, Union
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        return (await db.execute(select(User).where(User.email == email))).scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        create_data = obj_in.model_dump()
        create_data["hashed_password"] = get_password_hash(obj_in.password)
        del create_data["password"]

        db_obj = User(**create_data)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser(User)
