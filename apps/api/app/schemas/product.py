from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel


class ProductBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=512)
    description: Optional[str] = None
    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    inventory: int = Field(default=0, ge=0)
    image: Optional[str] = Field(default=None, max_length=2048)
    category: str = Field(default="uncategorized", index=True, max_length=255)
    tags: list[str] = Field(default_factory=list)
    rating: Optional[float] = Field(default=4.5, ge=0.0, le=5.0)
    is_active: bool = Field(default=True)


class ProductCreate(ProductBase):
    sku: str = Field(min_length=1, max_length=255)


class ProductUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=512)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    inventory: Optional[int] = Field(default=None, ge=0)
    image: Optional[str] = Field(default=None, max_length=2048)
    category: Optional[str] = Field(default=None, max_length=255)
    tags: Optional[list[str]] = None
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_active: Optional[bool] = None


class ProductRead(ProductBase):
    id: int
    sku: str

    model_config = {
        "from_attributes": True
    }


class Product(ProductRead):
    pass
