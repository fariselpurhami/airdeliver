# file: apps/api/app/schemas/product.py

from sqlmodel import SQLModel
from typing import Optional

class ProductBase(SQLModel):
    name: str
    description: str
    price: float
    inventory: int
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    inventory: Optional[int] = None
    image_url: Optional[str] = None

class Product(ProductBase):
    id: int

    # Correct configuration for Pydantic v2
    model_config = {
        "from_attributes": True
    }
