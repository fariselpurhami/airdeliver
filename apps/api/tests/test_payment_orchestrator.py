# apps/api/tests/test_payment_orchestrator.py
"""Tests for PaymentRequest validation and PaymentOrchestrator routing/failover."""
import asyncio
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.services.payment_orchestrator import (
    GatewayProvider,
    IPaymentGateway,
    GatewayResult,
    OrchestrationResponse,
    PaymentOrchestrator,
    PaymentRequest,
    PaymentStatus,
)


def make_request(**overrides):
    base = dict(
        order_id="ord-1",
        amount=Decimal("21.00"),
        currency="egp",
        region="eg",
        idempotency_key="idem_pay_1_42_1234567890",
    )
    base.update(overrides)
    return PaymentRequest(**base)


class FakeGateway(IPaymentGateway):
    def __init__(self, provider, result=None, exc=None, delay=0.0):
        self._provider = provider
        self._result = result
        self._exc = exc
        self._delay = delay
        self.calls = 0

    @property
    def provider(self):
        return self._provider

    async def create_payment_intent(self, request):
        self.calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc:
            raise self._exc
        return self._result


def ok_result(provider, secret="sec"):
    return GatewayResult(provider=provider, status=PaymentStatus.SUCCESS, client_secret=secret)


def fail_result(provider):
    return GatewayResult(provider=provider, status=PaymentStatus.FAILURE, error_message="declined")


# --- PaymentRequest DTO ---

def test_request_normalizes_currency_and_region_case():
    req = make_request(currency="egp", region="eg")
    assert req.currency == "EGP" and req.region == "EG"


def test_request_quantizes_amount_to_two_decimals():
    req = make_request(amount=Decimal("10.005"))
    assert req.amount == Decimal("10.01")  # ROUND_HALF_UP, no phantom fractions


def test_request_rejects_zero_and_negative_amounts():
    with pytest.raises(ValidationError):
        make_request(amount=Decimal("0"))
    with pytest.raises(ValidationError):
        make_request(amount=Decimal("-5"))


def test_request_rejects_short_idempotency_key():
    with pytest.raises(ValidationError):
        make_request(idempotency_key="short")


# --- Orchestrator routing ---

@pytest.mark.asyncio
async def test_routes_to_region_preferred_gateway():
    stripe = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE, "stripe_sec"))
    paypal = FakeGateway(GatewayProvider.PAYPAL, ok_result(GatewayProvider.PAYPAL, "paypal_sec"))
    orch = PaymentOrchestrator([stripe, paypal])
    resp = await orch.process_payment(make_request(region="EG"), "corr-1")
    assert resp.status == PaymentStatus.SUCCESS
    assert resp.primary_gateway.provider == GatewayProvider.STRIPE
    assert resp.alternative_gateways[0].provider == GatewayProvider.PAYPAL


@pytest.mark.asyncio
async def test_unknown_region_falls_back_to_default():
    stripe = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE))
    orch = PaymentOrchestrator([stripe])
    resp = await orch.process_payment(make_request(region="ZZ"), "corr-2")
    assert resp.status == PaymentStatus.SUCCESS
    assert resp.primary_gateway.provider == GatewayProvider.STRIPE


@pytest.mark.asyncio
async def test_no_gateway_for_region_is_clean_failure():
    orch = PaymentOrchestrator([])  # nothing configured
    resp = await orch.process_payment(make_request(region="EG"), "corr-3")
    assert resp.status == PaymentStatus.FAILURE
    assert "unavailable" in resp.error_message.lower()


@pytest.mark.asyncio
async def test_all_gateways_failing_returns_failure():
    stripe = FakeGateway(GatewayProvider.STRIPE, fail_result(GatewayProvider.STRIPE))
    paypal = FakeGateway(GatewayProvider.PAYPAL, fail_result(GatewayProvider.PAYPAL))
    orch = PaymentOrchestrator([stripe, paypal])
    resp = await orch.process_payment(make_request(region="EG"), "corr-4")
    assert resp.status == PaymentStatus.FAILURE
    assert resp.primary_gateway is None


@pytest.mark.asyncio
async def test_gateway_exception_is_trapped_not_propagated():
    stripe = FakeGateway(GatewayProvider.STRIPE, exc=RuntimeError("sdk exploded"))
    paypal = FakeGateway(GatewayProvider.PAYPAL, ok_result(GatewayProvider.PAYPAL, "pp"))
    orch = PaymentOrchestrator([stripe, paypal])
    resp = await orch.process_payment(make_request(region="EG"), "corr-5")
    assert resp.status == PaymentStatus.SUCCESS
    assert resp.primary_gateway.provider == GatewayProvider.PAYPAL


@pytest.mark.asyncio
async def test_slow_gateway_is_cancelled_but_fast_one_wins():
    stripe = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE), delay=30.0)
    paypal = FakeGateway(GatewayProvider.PAYPAL, ok_result(GatewayProvider.PAYPAL, "pp"), delay=0.05)
    orch = PaymentOrchestrator([stripe, paypal])
    orch.GLOBAL_TIMEOUT_SECONDS = 1.0
    resp = await orch.process_payment(make_request(region="EG"), "corr-6")
    assert resp.status == PaymentStatus.SUCCESS
    assert resp.primary_gateway.provider == GatewayProvider.PAYPAL


@pytest.mark.asyncio
async def test_all_gateways_slow_returns_latency_failure():
    stripe = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE), delay=30.0)
    orch = PaymentOrchestrator([stripe])
    orch.GLOBAL_TIMEOUT_SECONDS = 1.0
    resp = await orch.process_payment(make_request(region="EG"), "corr-7")
    assert resp.status == PaymentStatus.FAILURE
    assert "latency" in resp.error_message.lower()


@pytest.mark.asyncio
async def test_explicit_payment_choice_does_not_initialize_another_provider():
    stripe = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE))
    paypal = FakeGateway(GatewayProvider.PAYPAL, ok_result(GatewayProvider.PAYPAL))
    result = await PaymentOrchestrator([stripe, paypal]).process_payment(make_request(region="US", preferred_provider="paypal"), "choice")
    assert result.primary_gateway.provider == GatewayProvider.PAYPAL
    assert paypal.calls == 1
    assert stripe.calls == 0


def test_unconfigured_browser_gateway_is_not_advertised():
    gateway = FakeGateway(GatewayProvider.STRIPE, ok_result(GatewayProvider.STRIPE))
    assert PaymentOrchestrator([gateway]).available_providers == ["stripe"]
