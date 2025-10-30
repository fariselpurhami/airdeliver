# apps/api/app/api/v1/endpoints/webhooks.py

from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlmodel import Session
import stripe
from app.core.config import settings
from app.db.session import get_session

router = APIRouter()

@router.post("/stripe")
async def stripe_webhook(
    request: Request, 
    stripe_signature: str = Header(None),
    session: Session = Depends(get_session)
):

    try:
        payload = await request.body()
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=stripe_signature, secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e: 
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e: 
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata']['order_id']
        print(f"✅ Payment succeeded for Order ID: {order_id}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        order_id = payment_intent['metadata']['order_id']
        print(f"❌ Payment failed for Order ID: {order_id}")

    return {"status": "success"}
