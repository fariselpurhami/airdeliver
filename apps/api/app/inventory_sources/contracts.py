"""Provider-neutral contracts, no partner adapter or external I/O implementation."""
from datetime import datetime
from enum import Enum
from typing import Literal, Protocol
from uuid import UUID
from app.schemas.shipping import ShippingAddress
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LAUNCH_CATEGORIES=frozenset({'clothing','accessories','electronics','makeup','beauty','personal_care','sports'})

class Contract(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)

class Operation(str,Enum):
    CATALOG='catalog'
    PRICE='price'
    STOCK='stock'
    PLACE_ORDER='place_order'
    SHIPMENT='shipment'
    TRACKING='tracking'
    RETURNS='returns'
    RESERVE='reserve'
    COMMIT='commit'
    RELEASE='release'

class SourceIdentity(Contract):
    source_key: str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    seller_key: str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    kind: Literal['partner_merchant','airdeliver_own_stock']
    legal_seller_name: str=Field(min_length=2,max_length=200)
    inventory_country: Literal['US']
    seller_country: Literal['US']

class SourceTerms(Contract):
    version: str=Field(min_length=1,max_length=100)
    approval_reference: str | None=Field(default=None,min_length=5,max_length=200)
    approved: bool=False
    effective_at: datetime
    expires_at: datetime
    allowed_categories: frozenset[str]=Field(min_length=1)
    capabilities: frozenset[Operation]=Field(default_factory=frozenset)
    permitted_operations: frozenset[Operation]=Field(default_factory=frozenset)
    # Capabilities describe technical ability. Terms independently permit use.
    permits_airdeliver_checkout: bool=False
    permits_airdeliver_payment_collection: bool=False
    permits_airdeliver_branding: bool=False
    dispatch_business_days_max: int | None=Field(default=None,strict=True,ge=0,le=365)
    return_window_days: int | None=Field(default=None,strict=True,ge=1,le=365)
    return_policy_reference: str | None=Field(default=None,min_length=5,max_length=200)
    managed_label_account_reference: str | None=Field(default=None,min_length=2,max_length=100)

    @field_validator('effective_at','expires_at')
    @classmethod
    def aware(cls,value):
        if value.utcoffset() is None:raise ValueError('Timezone required')
        return value

    @field_validator('allowed_categories')
    @classmethod
    def categories(cls,value):
        if not value<=LAUNCH_CATEGORIES:raise ValueError('Category outside launch scope')
        return value

    @model_validator(mode='after')
    def valid(self):
        if self.expires_at<=self.effective_at:raise ValueError('Invalid terms interval')
        if self.approved and not self.approval_reference:raise ValueError('Approval source required')
        return self

class Money(Contract):
    amount_cents: int=Field(strict=True,ge=0,le=999999999)
    currency: Literal['USD']='USD'

class CatalogItem(Contract):
    external_product_id: str=Field(min_length=1,max_length=255)
    external_variant_id: str=Field(min_length=1,max_length=255)
    title: str=Field(min_length=1,max_length=255)
    category: str=Field(min_length=1,max_length=50)
    origin_reference: str=Field(min_length=1,max_length=255)

class PriceSnapshot(Contract):
    variant_id: str=Field(min_length=1,max_length=255)
    price: Money
    source_revision: str=Field(min_length=1,max_length=255)
    observed_at: datetime
    expires_at: datetime

    @model_validator(mode='after')
    def aware_fresh_interval(self):
        if self.observed_at.utcoffset() is None or self.expires_at.utcoffset() is None or self.expires_at<=self.observed_at:raise ValueError('Valid aware observation interval required')
        return self

class StockSnapshot(Contract):
    variant_id: str=Field(min_length=1,max_length=255)
    source_revision: str=Field(min_length=1,max_length=255)
    observed_at: datetime
    expires_at: datetime
    available: int=Field(strict=True,ge=0)
    origin_reference: str=Field(min_length=1,max_length=255)

    @model_validator(mode='after')
    def aware_fresh_interval(self):
        if self.observed_at.utcoffset() is None or self.expires_at.utcoffset() is None or self.expires_at<=self.observed_at:raise ValueError('Valid aware observation interval required')
        return self

class ReservationCommand(Contract):
    request_id: UUID
    source_key: str=Field(min_length=1,max_length=100)
    order_line_id: int=Field(strict=True,ge=1,le=2147483647)
    variant_id: str=Field(min_length=1,max_length=255)
    origin_reference: str=Field(min_length=1,max_length=255)
    quantity: int=Field(strict=True,ge=1,le=99)
    expected_source_revision: str=Field(min_length=1,max_length=255)
    expires_at: datetime
    fence: int=Field(strict=True,ge=1)
    _aware=field_validator('expires_at')(SourceTerms.aware.__func__)

class ReservationResult(Contract):
    request_id: UUID
    reservation_reference: str | None=Field(default=None,min_length=1,max_length=255)
    state: Literal['held','committed','released','refused','unknown']
    fence: int=Field(strict=True,ge=1)
    source_revision: str | None=Field(default=None,min_length=1,max_length=255)
    expires_at: datetime | None=None

    @model_validator(mode='after')
    def held_evidence(self):
        if self.state=='held' and (not self.reservation_reference or self.expires_at is None or self.expires_at.utcoffset() is None):raise ValueError('Held stock requires a reference and aware expiry')
        return self

class PurchaseLine(Contract):
    order_line_id: int=Field(strict=True,ge=1,le=2147483647)
    variant_id: str=Field(min_length=1,max_length=255)
    quantity: int=Field(strict=True,ge=1,le=99)
    unit_price: Money
    origin_reference: str=Field(min_length=1,max_length=255)
    reservation_reference: str=Field(min_length=1,max_length=255)

class PlaceOrder(Contract):
    request_id: UUID
    source_key: str=Field(min_length=1,max_length=100)
    lines: list[PurchaseLine]=Field(min_length=1,max_length=100)
    shipping_address: ShippingAddress
    paid_receipt_reference: str=Field(min_length=1,max_length=255)

    @model_validator(mode='after')
    def unique(self):
        if len({line.order_line_id for line in self.lines})!=len(self.lines):raise ValueError('Duplicate order line')
        return self

class SourceEvent(Contract):
    source_key: str=Field(min_length=1,max_length=100)
    event_id: str=Field(min_length=1,max_length=255)
    external_order_id: str=Field(min_length=1,max_length=255)
    shipment_id: str | None=Field(default=None,min_length=1,max_length=255)
    kind: Literal['order_accepted','order_refused','label_created','carrier_accepted','in_transit','delivered','exception','return_received','refund_confirmed']
    occurred_at: datetime
    source_revision: str=Field(min_length=1,max_length=255)
    evidence_reference: str=Field(min_length=1,max_length=255)
    _aware=field_validator('occurred_at')(SourceTerms.aware.__func__)

class SourceReturn(Contract):
    request_id: UUID
    external_order_id: str=Field(min_length=1,max_length=255)
    external_line_id: str=Field(min_length=1,max_length=255)
    quantity: int=Field(strict=True,ge=1,le=99)
    reason: str=Field(min_length=2,max_length=200)
    approved_policy_reference: str=Field(min_length=5,max_length=200)

class OperationResult(Contract):
    request_id: UUID
    state: Literal['accepted','refused','unknown']
    external_reference: str | None=Field(default=None,min_length=1,max_length=255)
    evidence_reference: str | None=Field(default=None,min_length=1,max_length=255)

class CatalogPage(Contract):
    items: list[CatalogItem]=Field(max_length=100)
    next_cursor: str | None=Field(default=None,max_length=2000)

class InventorySourceAdapter(Protocol):
    identity: SourceIdentity
    async def catalog(self, cursor: str | None=None) -> CatalogPage: ...
    async def price(self, variant_id: str) -> PriceSnapshot: ...
    async def stock(self, variant_id: str, origin_reference: str) -> StockSnapshot: ...
    async def place_order(self, command: PlaceOrder) -> OperationResult: ...
    async def shipment_events(self, cursor: str | None=None) -> list[SourceEvent]: ...
    async def tracking_events(self, external_order_id: str) -> list[SourceEvent]: ...
    async def request_return(self, command: SourceReturn) -> OperationResult: ...
    async def reserve(self, command: ReservationCommand) -> ReservationResult: ...
    async def commit(self, command: ReservationCommand, reservation_reference: str) -> ReservationResult: ...
    async def release(self, command: ReservationCommand, reservation_reference: str) -> ReservationResult: ...


def operation_gate(terms: SourceTerms, operation: Operation, category: str, *, now: datetime) -> tuple[str,...]:
    """Only trusted stored terms may reach this gate, never client-supplied flags."""
    if now.utcoffset() is None:raise ValueError('Timezone required')
    reasons=[]
    if not terms.approved:reasons.append('terms_not_approved')
    if not terms.effective_at<=now<terms.expires_at:reasons.append('terms_not_current')
    if category not in LAUNCH_CATEGORIES or category not in terms.allowed_categories:reasons.append('category_not_permitted')
    if operation not in terms.capabilities:reasons.append('capability_unavailable')
    if operation not in terms.permitted_operations:reasons.append('operation_not_permitted')
    if operation in {Operation.PLACE_ORDER,Operation.RESERVE,Operation.COMMIT}:
        if not terms.permits_airdeliver_checkout:reasons.append('checkout_not_permitted')
        if not terms.permits_airdeliver_payment_collection:reasons.append('payment_collection_not_permitted')
        if not terms.permits_airdeliver_branding:reasons.append('branding_not_permitted')
    if operation==Operation.RETURNS and not terms.return_policy_reference:reasons.append('return_policy_unverified')
    return tuple(reasons)
