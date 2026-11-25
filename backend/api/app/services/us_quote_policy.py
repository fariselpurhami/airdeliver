"""Offline US quote preparation, never a payment authorization or tax engine.

The caller must supply authoritative catalog snapshots and an address-bound,
reviewed tax assessment. Nothing in this module is wired into live checkout.
"""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.shipping import ShippingAddress, US_REGIONS


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Line(StrictInput):
    product_id: int = Field(strict=True, ge=1, le=2147483647)
    quantity: int = Field(strict=True, ge=1, le=99)
    unit_price_cents: int = Field(strict=True, ge=0, le=999999999)
    currency: Literal['USD'] = 'USD'
    available: int = Field(strict=True, ge=0)
    active: bool = Field(strict=True)


class USShippingPolicy(StrictInput):
    version: str = Field(min_length=1, max_length=100)
    approved_reference: str = Field(min_length=5, max_length=200)
    regions: frozenset[str] = Field(min_length=1)
    flat_cents: int = Field(strict=True, ge=0, le=999999999)
    free_at_cents: int | None = Field(default=None, strict=True, ge=0, le=999999999)
    expires_at: datetime

    @field_validator('regions')
    @classmethod
    def known_regions(cls, value):
        if not value.issubset(US_REGIONS):
            raise ValueError('Unknown US service region')
        return value

    @field_validator('expires_at')
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError('Timezone required')
        return value


class TaxAssessment(StrictInput):
    """Final tax including any taxable shipping, from a reviewed external source.

    A zero amount needs the same explicit review as a positive amount. This is
    data to validate, not evidence the source/approver is actually authorized.
    """
    quote_basis_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    amount_cents: int = Field(strict=True, ge=0, le=999999999)
    source_reference: str = Field(min_length=5, max_length=200)
    reviewed_by: str = Field(min_length=2, max_length=100)
    expires_at: datetime

    @field_validator('expires_at')
    @classmethod
    def aware(cls, value):
        if value.utcoffset() is None:
            raise ValueError('Timezone required')
        return value


class QuoteInput(StrictInput):
    address: ShippingAddress
    lines: list[Line] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique(self):
        if len({line.product_id for line in self.lines}) != len(self.lines):
            raise ValueError('Aggregate duplicate product lines before quoting')
        return self


def quote_basis(request: QuoteInput, policy: USShippingPolicy, *, now: datetime) -> dict:
    if now.utcoffset() is None:
        raise ValueError('Timezone required')
    if policy.expires_at <= now:
        raise ValueError('Shipping policy expired')
    if request.address.region not in policy.regions:
        raise ValueError('Destination is outside configured service area')
    for line in request.lines:
        if not line.active or line.available < line.quantity:
            raise ValueError('Catalog item unavailable or insufficient stock')
    subtotal = sum(line.quantity * line.unit_price_cents for line in request.lines)
    if subtotal <= 0 or subtotal > 999999999:
        raise ValueError('Subtotal outside supported bounds')
    shipping = 0 if policy.free_at_cents is not None and subtotal >= policy.free_at_cents else policy.flat_cents
    # Do not publish the address. Digest is an integrity binding, not encryption.
    basis = {'address': request.address.model_dump(mode='json'),
             'lines': sorted([{'product_id': line.product_id, 'quantity': line.quantity,
                               'unit_price_cents': line.unit_price_cents, 'currency': line.currency}
                              for line in request.lines], key=lambda line: line['product_id']),
             'shipping_cents': shipping, 'policy_version': policy.version,
             'policy_reference': policy.approved_reference}
    digest = sha256(json.dumps(basis, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'quote_basis_sha256': digest, 'subtotal_cents': subtotal, 'shipping_cents': shipping}


def prepare_quote(request: QuoteInput, policy: USShippingPolicy, tax: TaxAssessment, *, now: datetime) -> dict:
    basis = quote_basis(request, policy, now=now)
    if tax.expires_at <= now or tax.quote_basis_sha256 != basis['quote_basis_sha256']:
        raise ValueError('Tax assessment expired or does not match destination/items/shipping')
    total = basis['subtotal_cents'] + basis['shipping_cents'] + tax.amount_cents
    if total > 999999999:
        raise ValueError('Total outside supported bounds')
    return {**basis, 'tax_cents': tax.amount_cents, 'total_cents': total,
            'currency': 'USD', 'display_total': str((Decimal(total) / 100).quantize(Decimal('.01'))),
            'policy_version': policy.version, 'tax_source_reference': tax.source_reference,
            'expires_at': min(policy.expires_at, tax.expires_at).isoformat(),
            'ready_for_payment': False, 'stock_reserved': False,
            'mode': 'offline_review_only'}
