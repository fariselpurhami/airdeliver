# apps/api/app/schemas/product.py

from decimal import Decimal
from typing import Any, Optional

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel


class ProductBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=512)
    description: Optional[str] = Field(default=None, max_length=8192)
    price: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    inventory: int = Field(default=0, ge=0)
    image: Optional[str] = Field(default=None, max_length=2048)
    category: str = Field(default="uncategorized", index=True, min_length=1, max_length=255)
    tags: list[str] = Field(default_factory=list, max_length=100)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_active: bool = Field(default=True)

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, value: Any) -> Decimal:
        if isinstance(value, (str, int)):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        return value


class ProductCreate(ProductBase):
    sku: str = Field(min_length=1, max_length=255)


class ProductUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=512)
    description: Optional[str] = Field(default=None, max_length=8192)
    price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    inventory: Optional[int] = Field(default=None, ge=0)
    image: Optional[str] = Field(default=None, max_length=2048)
    category: Optional[str] = Field(default=None, min_length=1, max_length=255)
    tags: Optional[list[str]] = Field(default=None, max_length=100)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_active: Optional[bool] = None

    @field_validator("price", mode="before")
    @classmethod
    def parse_price_update(cls, value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        if isinstance(value, (str, int)):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        return value


class ProductRead(ProductBase):
    attributes: dict[str, str] = Field(default_factory=dict)
    id: int
    sku: str

    model_config = ConfigDict(from_attributes=True)


class Product(ProductRead):
    pass
