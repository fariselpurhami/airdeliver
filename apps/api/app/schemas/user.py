# file: apps/api/app/schemas/user.py

from sqlmodel import SQLModel
from pydantic import EmailStr
from typing import Optional
from app.models.user import UserRole

class UserBase(SQLModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int

    # Correct configuration for Pydantic v2
    model_config = {
        "from_attributes": True
    }

class User(UserInDB):
    pass
