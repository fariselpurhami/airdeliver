from sqlmodel import SQLModel, Field
from typing import Optional

class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    price: float
    inventory: int = 0
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    inventory: Optional[int] = None
    image_url: Optional[str] = None

class ProductRead(ProductBase):
    id: int
    model_config = {
        "from_attributes": True
    }

class Product(ProductRead):
    pass
