"""Preparation contracts only. No ticket, RMA, label, refund or SLA is created."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictContract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ReturnPolicyDraft(StrictContract):
    version: str = Field(min_length=1,max_length=100)
    seller_reference: str = Field(min_length=1,max_length=100)
    approval_state: Literal['proposed','approved']
    approval_reference: str | None = Field(default=None,min_length=5,max_length=200)
    # No default window. Thirty days is an open proposal, not an entitlement.
    window_days_from_delivery: int = Field(strict=True,ge=1,le=365)
    window_clock: Literal['calendar_days_in_destination_timezone']
    destination_timezone: str = Field(min_length=3,max_length=100)
    return_shipping_payer: Literal['customer','seller','airdeliver','case_review']
    original_shipping_refund: Literal['included','excluded','case_review']
    restocking_fee: Literal['none','case_review']
    allowed_condition_codes: frozenset[str] = Field(min_length=1,max_length=20)
    excluded_category_codes: frozenset[str] = Field(default_factory=frozenset,max_length=100)
    support_queue_reference: str = Field(min_length=2,max_length=100)
    effective_at: datetime
    expires_at: datetime

    @field_validator('effective_at','expires_at')
    @classmethod
    def timezone_required(cls,value):
        if value.utcoffset() is None:
            raise ValueError('Timezone required')
        return value

    @field_validator('destination_timezone')
    @classmethod
    def known_timezone(cls,value):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        try:ZoneInfo(value)
        except ZoneInfoNotFoundError:raise ValueError('Unknown destination timezone')
        return value

    @model_validator(mode='after')
    def valid_policy(self):
        if self.expires_at<=self.effective_at:
            raise ValueError('Expiry must follow effective time')
        if self.approval_state=='approved' and self.approval_reference is None:
            raise ValueError('An approved policy requires a source reference')
        return self


class ReturnLine(StrictContract):
    order_line_id: int = Field(strict=True,ge=1,le=2147483647)
    quantity: int = Field(strict=True,ge=1,le=99)
    reason: Literal['damaged','wrong_item','not_as_described','changed_mind','other']
    condition_code: str = Field(min_length=1,max_length=50)


class SupportIntakeDraft(StrictContract):
    request_id: UUID
    order_id: int = Field(strict=True,ge=1,le=2147483647)
    kind: Literal['return','delivery_problem','payment_problem','other']
    message: str = Field(min_length=10,max_length=2000)
    lines: list[ReturnLine] = Field(default_factory=list,max_length=100)

    @model_validator(mode='after')
    def unique_lines(self):
        if self.kind=='return' and not self.lines:
            raise ValueError('Select the purchased items and quantities')
        if len({line.order_line_id for line in self.lines})!=len(self.lines):
            raise ValueError('Duplicate order line')
        return self


def intake_availability(*, policy: ReturnPolicyDraft | None, queue_owner_verified: bool, now: datetime) -> dict:
    """Readiness description, deliberately not an eligibility/acceptance decision.

    The eventual server must verify policy approval and queue ownership from
    authenticated records. User-supplied flags or reference strings prove neither.
    """
    reasons=[]
    if now.utcoffset() is None:
        raise ValueError('Timezone required')
    if policy is None or policy.approval_state!='approved':reasons.append('return_policy_not_approved')
    if policy is not None and not policy.effective_at<=now<policy.expires_at:reasons.append('policy_not_current')
    if not queue_owner_verified:reasons.append('support_queue_owner_not_verified')
    return {'configuration_ready':not reasons,'blocked_reasons':reasons,
            'intake_enabled':False,'ticket_created':False,'refund_started':False,
            'return_accepted':False,'mode':'design_only'}
