# file: apps/api/app/api/v1/endpoints/webhooks.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlmodel import Session
import stripe

from app.core.config import settings
from app.db.session import get_session
# from app.crud import crud_order # Assuming you have order CRUD functions

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request, 
    stripe_signature: str = Header(None),
    session: Session = Depends(get_session)
):
    """
    Handle webhooks from Stripe to update order status.
    """
    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature, secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e: # Invalid payload
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e: # Invalid signature
        raise HTTPException(status_code=400, detail=str(e))

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata']['order_id']
        print(f"✅ Payment succeeded for Order ID: {order_id}")
        # TODO: Update order status in the database
        # order = crud_order.get(session, id=int(order_id))
        # if order:
        #     crud_order.update(session, db_obj=order, obj_in={"status": "processing"})

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata']['order_id']
        print(f"❌ Payment failed for Order ID: {order_id}")
        # TODO: Update order status to 'failed' and notify the user

    return {"status": "success"}
