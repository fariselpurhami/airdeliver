"""Simulation must never masquerade as a real STK push."""
from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.services.payment_orchestrator import MpesaGateway, PaymentRequest, PaymentStatus


def request():
    return PaymentRequest(order_id="7", amount=Decimal("10.00"), currency="KES", region="KE",
                          idempotency_key="payment-order-7-key", metadata={"phone_number": "254700000000"})


def gateway(enabled=False, base="https://sandbox.safaricom.co.ke"):
    return MpesaGateway(SimpleNamespace(MPESA_SIMULATION_ENABLED=enabled, MPESA_API_BASE_URL=base), None, None)


@pytest.mark.asyncio
async def test_mpesa_default_cannot_claim_a_real_pin_request_was_sent():
    result = await gateway().create_payment_intent(request())
    assert result.status == PaymentStatus.FAILURE
    assert result.transaction_id is None


@pytest.mark.asyncio
async def test_mpesa_simulation_never_runs_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    result = await gateway(enabled=True).create_payment_intent(request())
    assert result.status == PaymentStatus.FAILURE


@pytest.mark.asyncio
async def test_mpesa_explicit_dev_sandbox_simulation_is_clearly_labeled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    result = await gateway(enabled=True).create_payment_intent(request())
    assert result.status == PaymentStatus.PENDING_CONFIRMATION
    assert result.transaction_id.startswith("simulated_")
    assert result.raw_response["simulated"] is True
    assert "no STK push was sent" in result.raw_response["message"]


@pytest.mark.asyncio
async def test_mpesa_simulation_rejects_live_endpoint_even_in_dev(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    result = await gateway(enabled=True, base="https://api.safaricom.co.ke").create_payment_intent(request())
    assert result.status == PaymentStatus.FAILURE
