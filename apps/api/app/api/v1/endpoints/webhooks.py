# apps/api/app/api/v1/endpoints/webhooks.py

import stripe
import logging
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.core.config import get_core_settings, CoreSettings
from app.api.deps import get_async_session
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
from app.services.payment_completion_service import PaymentCompletionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):

    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.critical("🚨 Security Risk: Stripe webhook secret is missing.")
        raise HTTPException(status_code=500, detail="Configuration Error")

    payload = await request.body()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except ValueError:
        logger.warning("⚠️ Webhook Error: Invalid payload received.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("🚨 Security Alert: Invalid Stripe signature detected.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        await _delegate_payment_success(data_object, session, rabbitmq, cache)
    
    elif event_type == "payment_intent.payment_failed":
        await _delegate_payment_failure(data_object, session, rabbitmq)

    return {"status": "success"}


async def _delegate_payment_success(payment_intent: dict, session: AsyncSession, rabbitmq: RabbitMQService, cache=None):

    metadata = payment_intent.get("metadata", {})
    order_id = metadata.get("order_id")
    user_id = metadata.get("user_id")
    transaction_id = payment_intent.get("id")

    if not order_id or not user_id:
        logger.error(f"❌ Missing metadata in PaymentIntent {transaction_id}")
        return

    completion_service = PaymentCompletionService(session, rabbitmq, cache)
    
    try:
        await completion_service.finalize_successful_payment(
            order_id=int(order_id),
            user_id=int(user_id),
            transaction_id=transaction_id
        )
    except Exception as e:
        logger.error(f"Failed to process success for Order {order_id}: {e}")

async def _delegate_payment_failure(payment_intent: dict, session: AsyncSession, rabbitmq: RabbitMQService):

    metadata = payment_intent.get("metadata", {})
    order_id = metadata.get("order_id")
    user_id = metadata.get("user_id")
    
    if not order_id: 
        return

    try:
        order = await session.get(Order, int(order_id))
        
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.FAILED
            session.add(order)
            await session.commit()
            
            logger.warning(f"❌ Payment declined for Order {order_id}. Reason: {payment_intent.get('last_payment_error')}")

            if user_id:
                await rabbitmq.publish(
                    body={
                        "user_id": int(user_id),
                        "content": "Payment authorization failed. Please check your card or funds.",
                        "type": "error"
                    },
                    routing_key="airdeliver.ai.response.out"
                )
    except Exception as e:
        logger.error(f"Database error while handling failure for Order {order_id}: {e}")
