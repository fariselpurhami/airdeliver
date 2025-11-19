# apps/api/app/api/v1/endpoints/webhooks.py

import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
import stripe
from app.core.config import get_stripe_settings, StripeSettings
from app.db.session import get_session
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    session: AsyncSession = Depends(get_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    stripe_settings: StripeSettings = Depends(get_stripe_settings),
):
    """
    Production-Grade Webhook Handler for Stripe.
    1. Verifies Security Signature.
    2. Updates Order State (Idempotent).
    3. Triggers Async Events (Notification + Drone Mission).
    """
    
    if not stripe_settings.STRIPE_WEBHOOK_SECRET:
        logger.critical("Stripe webhook secret is missing in configuration.")
        raise HTTPException(status_code=500, detail="Webhook configuration error.")

    payload = await request.body()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=stripe_settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "payment_intent.succeeded":
        await _handle_payment_success(event, session, rabbitmq)
    
    elif event["type"] == "payment_intent.payment_failed":
        await _handle_payment_failure(event, session, rabbitmq)

    return {"status": "success"}


async def _handle_payment_success(event, session: AsyncSession, rabbitmq: RabbitMQService):
    """
    Handles successful payments:
    - Updates DB to PROCESSING.
    - Notifies User via WebSocket.
    - Triggers Mission Planning via Event Bus.
    """
    payment_intent = event["data"]["object"]
    order_id = payment_intent.get("metadata", {}).get("order_id")
    user_id = payment_intent.get("metadata", {}).get("user_id") 

    if not order_id:
        logger.warning("Payment succeeded but missing order_id in metadata.")
        return

    order = await session.get(Order, int(order_id))
    if not order:
        logger.error(f"Order {order_id} not found for successful payment.")
        return

    if order.status in [OrderStatus.PENDING, OrderStatus.SAVED_FOR_LATER]:
        order.status = OrderStatus.PROCESSING 
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        logger.info(f"💰 Order {order_id} paid successfully. Amount: {order.total_price}")

        await rabbitmq.publish(
            body={
                "user_id": order.user_id,
                "content": f"**Payment Authorized!** 💳\nOrder #{order_id} is confirmed. Initializing drone mission sequence...",
                "type": "success_text"
            },
            routing_key="airdeliver.ai.response.out"
        )

        await rabbitmq.publish(
            body={
                "event": "ORDER_PAID",
                "order_id": order.id,
                "user_id": order.user_id,
                "location": {
                    "lat": order.delivery_lat,
                    "lon": order.delivery_lon
                }
            },
            routing_key="airdeliver.events.order.paid",
            exchange_name="drone.events" 
        )
    else:
        logger.info(f"Order {order_id} already processed (Status: {order.status}). Skipping.")


async def _handle_payment_failure(event, session: AsyncSession, rabbitmq: RabbitMQService):
    payment_intent = event["data"]["object"]
    order_id = payment_intent.get("metadata", {}).get("order_id")

    if not order_id:
        return

    order = await session.get(Order, int(order_id))
    if order and order.status == OrderStatus.PENDING:
        order.status = OrderStatus.FAILED
        session.add(order)
        await session.commit()
        
        logger.warning(f"❌ Payment failed for Order {order_id}.")

        await rabbitmq.publish(
            body={
                "user_id": order.user_id,
                "content": "Payment authorization failed. Please check your card details or try a different method.",
                "type": "error"
            },
            routing_key="airdeliver.ai.response.out"
        )
