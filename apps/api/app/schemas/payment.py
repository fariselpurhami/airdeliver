from pydantic import BaseModel, Field
from typing import Optional

class PaymentIntent(BaseModel):
    """
    Represents the data returned after creating a payment intent.
    It uses aliases to handle the camelCase from the payment provider (e.g., Stripe)
    while maintaining snake_case in Python.
    """
    status: str
    provider: str
    payment_id: str = Field(..., alias="paymentId")
    client_secret: Optional[str] = Field(None, alias="clientSecret")
    error: Optional[str] = None

    # Updated configuration for Pydantic v2
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "status": "requires_payment_method",
                "provider": "stripe",
                "paymentId": "pi_12345",
                "clientSecret": "pi_12345_secret_abcde",
                "error": None,
            }
        }
    }
