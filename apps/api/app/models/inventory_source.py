"""Additive provenance side tables. Existing products/orders stay untouched."""
from datetime import datetime,timezone
from typing import Optional
from sqlalchemy import Column,JSON,DateTime,UniqueConstraint
from sqlmodel import SQLModel,Field

class InventorySource(SQLModel,table=True):
    __tablename__='inventory_sources'
    id: Optional[int]=Field(default=None,primary_key=True)
    source_key: str=Field(unique=True,max_length=100)
    seller_key: str=Field(index=True,max_length=100)
    # Validated against SourceIdentity/SourceTerms at the service boundary.
    identity: dict=Field(sa_column=Column(JSON,nullable=False))
    terms: dict=Field(sa_column=Column(JSON,nullable=False))
    enabled: bool=Field(default=False)

class ProductSourceBinding(SQLModel,table=True):
    __tablename__='product_source_bindings'
    __table_args__=(UniqueConstraint('source_id','external_variant_id','origin_reference',name='uq_source_variant_origin'),)
    product_id: int=Field(primary_key=True,foreign_key='products.id')
    source_id: int=Field(foreign_key='inventory_sources.id',index=True)
    external_product_id: str=Field(max_length=255)
    external_variant_id: str=Field(max_length=255)
    origin_reference: str=Field(max_length=255)
    category: str=Field(max_length=50)

class OrderLineSourceSnapshot(SQLModel,table=True):
    __tablename__='order_line_source_snapshots'
    order_item_id: int=Field(primary_key=True,foreign_key='order_items.id')
    source_id: int=Field(foreign_key='inventory_sources.id',index=True)
    # Historical identity/terms must not follow mutable listing/source updates.
    snapshot: dict=Field(sa_column=Column(JSON,nullable=False))
    created_at: datetime=Field(default_factory=lambda:datetime.now(timezone.utc),sa_column=Column(DateTime(timezone=True),nullable=False))
