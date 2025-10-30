# apps/api/app/schemas/user.py

from sqlmodel import SQLModel, Field
from pydantic import EmailStr
from typing import Optional
from app.models.user import UserRole

class UserBase(SQLModel):
    email: EmailStr = Field(index=True)
    is_active: bool = True
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.USER)
    phone_number: Optional[str] = Field(default=None, index=True, nullable=True)
    address: Optional[str] = Field(default=None, nullable=True)
    avatar_url: Optional[str] = Field(default=None, nullable=True)

class UserCreate(UserBase):
    password: str

class UserUpdate(SQLModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class UserRead(UserBase):
    id: int
    model_config = {
        "from_attributes": True
    }

class UserInDBBase(UserBase):
    id: int
    hashed_password: Optional[str] = None
    model_config = {
        "from_attributes": True
    }

class User(UserRead):
    pass
