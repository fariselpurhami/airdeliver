from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app import schemas
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.services.payment_orchestrator import payment_orchestrator

router = APIRouter()

@router.post("/create-payment-intent", response_model=schemas.PaymentIntent)
def create_payment_intent(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    items: List[schemas.OrderItemCreate],
):
    """
    Creates a payment intent for the given items in the cart.
    The total amount is calculated on the backend to prevent tampering.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Cannot create payment for an empty cart.")

    total_price = 0
    for item in items:
        product = session.get(Product, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with id {item.product_id} not found")
        total_price += product.price * item.quantity

    # Use the payment orchestrator to create the payment with Stripe
    payment_info = payment_orchestrator.process_payment(
        amount=total_price, 
        currency="usd",
        region="US" # This could be determined from user profile or IP in a real app
    )

    # Check if the orchestrator failed to create an intent
    if "error" in payment_info or not payment_info.get("clientSecret"):
        raise HTTPException(
            status_code=500, 
            detail=payment_info.get("error", "Failed to create payment intent with the provider.")
        )
    
    # Return the full payment info object, which will be validated by the response_model
    return payment_info

