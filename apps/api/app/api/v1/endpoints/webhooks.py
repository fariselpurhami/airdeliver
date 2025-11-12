# apps/api/app/api/v1/endpoints/webhooks.py

from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import stripe
from app.core.config import settings
from app.db.session import get_session
from app.models.order import Order
from app.models.enums import OrderStatus

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500, detail="Stripe webhook secret is not configured."
        )

    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        order_id = payment_intent.get("metadata", {}).get("order_id")

        if not order_id:
            print("Webhook received: payment_intent.succeeded, but NO order_id in metadata.")
            raise HTTPException(
                status_code=400, detail="Missing order_id in payment metadata."
            )

        order = await session.get(Order, int(order_id))
        if not order:
            print(f"Webhook error: Order ID {order_id} not found in database.")
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.PROCESSING
            session.add(order)
            await session.commit()
            print(f"✅ Payment succeeded. Order ID: {order_id} status updated to PROCESSING.")

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        order_id = payment_intent.get("metadata", {}).get("order_id")

        if not order_id:
            print(
                "Webhook received: payment_intent.payment_failed, but NO order_id in metadata."
            )
            return {"status": "success", "detail": "Missing order_id, but acknowledged."}

        order = await session.get(Order, int(order_id))
        if not order:
            print(f"Webhook error: Order ID {order_id} not found in database.")
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")

        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.FAILED
            session.add(order)
            await session.commit()
            print(f"❌ Payment failed. Order ID: {order_id} status updated to FAILED.")

    return {"status": "success"}
