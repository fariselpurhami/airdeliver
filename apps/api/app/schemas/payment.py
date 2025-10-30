# apps/api/app/schemas/payment.py

from pydantic import BaseModel, Field
from typing import Optional

class PaymentIntent(BaseModel):

    status: str
    provider: str
    payment_id: str = Field(..., alias="paymentId")
    client_secret: Optional[str] = Field(None, alias="clientSecret")
    error: Optional[str] = None

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
