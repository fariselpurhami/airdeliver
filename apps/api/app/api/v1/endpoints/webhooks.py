"""Payment callbacks: authenticate first, bind provider facts, fail retryably."""
import json
import logging
from decimal import Decimal, InvalidOperation

import httpx
import stripe
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_stripe_settings, StripeSettings, get_paypal_settings, PayPalSettings
from app.api.deps import get_async_session
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
from app.services.payment_completion_service import PaymentCompletionService
from app.services.payment_orchestrator import PayPalGateway
from app.services.ai_checkout_service import AICheckoutService

logger = logging.getLogger(__name__)
router = APIRouter()
MAX_WEBHOOK_BYTES = 262144


async def _read_bounded_body(request: Request) -> bytes:
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Webhook body too large")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    settings: StripeSettings = Depends(get_stripe_settings),
    session: AsyncSession = Depends(get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    payload = await _read_bounded_body(request)
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET.get_secret_value()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature or "",
            secret=webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature or payload")

    try:
        event_type = event["type"]
        data_object = event["data"]["object"]
        # Do not claim a Redis key before durable work. Failed callbacks must
        # remain retryable; the locked Order state is the current mutation guard.
        if event_type == "payment_intent.succeeded":
            await _delegate_payment_success(data_object, session, rabbitmq, cache)
        elif event_type == "payment_intent.payment_failed":
            await _delegate_payment_failure(data_object, session, rabbitmq)
    except (ValueError, KeyError, TypeError, InvalidOperation):
        logger.warning("stripe_webhook_order_verification_failed")
        raise HTTPException(status_code=400, detail="Payment does not match the local order")
    except Exception:
        logger.error("stripe_webhook_processing_failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Payment processing temporarily unavailable")
    return {"status": "success"}


async def _delegate_payment_success(payment_intent: dict, session: AsyncSession, rabbitmq: RabbitMQService, cache=None):
    metadata = payment_intent.get("metadata", {})
    order_id, user_id = int(metadata["order_id"]), int(metadata["user_id"])
    transaction_id = payment_intent["id"]
    order = await session.get(Order, order_id)
    if not order or order.user_id != user_id or order.payment_transaction_id != transaction_id:
        raise ValueError("Payment order/owner/reference mismatch")
    amount_received = payment_intent.get("amount_received")
    expected = Decimal(str(order.total_price)) * 100
    if (isinstance(amount_received, bool) or not isinstance(amount_received, int)
            or not expected.is_finite() or expected <= 0 or Decimal(amount_received) != expected
            or payment_intent.get("currency", "").upper() != AICheckoutService.DEFAULT_CURRENCY.upper()):
        raise ValueError("Payment amount/currency mismatch")
    completion_service = PaymentCompletionService(session, rabbitmq, cache)
    # Propagate failures. A successful HTTP ack must not hide failed settlement.
    await completion_service.finalize_successful_payment(order_id, user_id, transaction_id)


async def _delegate_payment_failure(payment_intent: dict, session: AsyncSession, rabbitmq: RabbitMQService):
    metadata = payment_intent.get("metadata", {})
    order_id, user_id = int(metadata["order_id"]), int(metadata["user_id"])
    result = await session.execute(select(Order).where(Order.id == order_id).with_for_update())
    order = result.scalars().one_or_none()
    if not order or order.user_id != user_id or order.payment_transaction_id != payment_intent.get("id"):
        raise ValueError("Failed payment reference mismatch")
    if order.status == OrderStatus.PENDING and not order.is_paid:
        order.status = OrderStatus.FAILED
        session.add(order)
        await session.commit()
        await rabbitmq.publish({"user_id": user_id, "content": "Payment authorization failed. Please check your payment method.",
                                "type": "error"}, "airdeliver.ai.response.out")


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    settings: PayPalSettings = Depends(get_paypal_settings),
    session: AsyncSession = Depends(get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    payload = await _read_bounded_body(request)
    try:
        event = json.loads(payload)
        if not isinstance(event, dict):
            raise ValueError("Expected webhook object")
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    if not settings.PAYPAL_WEBHOOK_ID:
        raise HTTPException(status_code=503, detail="PayPal webhook is not configured")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            gateway = PayPalGateway(settings, cache, client)
            if not await gateway.verify_webhook_signature(event, request.headers):
                raise HTTPException(status_code=400, detail="Invalid webhook signature")
            if event.get("event_type") != "PAYMENT.CAPTURE.COMPLETED":
                return {"status": "ignored"}
            resource = event["resource"]
            paypal_order_id = resource["supplementary_data"]["related_ids"]["order_id"]
            details = await gateway.get_order_details(paypal_order_id)
            unit = details["purchase_units"][0]
            order_id, user_id = int(unit["reference_id"]), int(unit["custom_id"])
            order = await session.get(Order, order_id)
            if not order or order.user_id != user_id or order.payment_transaction_id != paypal_order_id:
                raise ValueError("PayPal local order reference mismatch")
            gateway.validate_order_details(
                details, paypal_order_id, expected_order_id=order_id, expected_user_id=user_id,
                expected_amount=Decimal(str(order.total_price)), expected_currency=AICheckoutService.DEFAULT_CURRENCY,
                require_completed=True,
            )
            capture_ids = {capture["id"] for capture in unit["payments"]["captures"]}
            if resource.get("status") != "COMPLETED" or resource.get("id") not in capture_ids:
                raise ValueError("PayPal webhook capture does not match verified funds")
            await PaymentCompletionService(session, rabbitmq, cache).finalize_successful_payment(
                order_id, user_id, paypal_order_id)
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, IndexError, InvalidOperation):
        logger.warning("paypal_webhook_order_verification_failed")
        raise HTTPException(status_code=400, detail="Payment does not match the local order")
    except Exception:
        logger.error("paypal_webhook_processing_failed", exc_info=True)
        raise HTTPException(status_code=503, detail="Payment processing temporarily unavailable")
    return {"status": "success"}
