# apps/api/app/schemas/ai_actions.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Optional, Union, Dict, Any
import orjson

def orjson_dumps(v, *, default):
    return orjson.dumps(v, default=default).decode()

class CartActionPayload(BaseModel):
    userId: str
    sku: str
    qty: int

class CartRemoveRollback(BaseModel):
    action: Literal["cart_remove"]
    payload: CartActionPayload

class AddToCartAction(BaseModel):
    action: Literal["add_to_cart"]
    payload: CartActionPayload
    rollback: CartRemoveRollback
    requires_mfa: bool = False

class TrackOrderAction(BaseModel):
    action: Literal["track_order"]
    payload: Dict[str, str]  
    rollback: None = None
    requires_mfa: bool = False

class ProductSearchAction(BaseModel):
    action: Literal["product_search"]
    payload: Dict[str, str]  
    rollback: None = None
    requires_mfa: bool = False

class SupportHandoffAction(BaseModel):
    action: Literal["initiate_support_handoff"]
    payload: Dict[str, Any] | None = None 
    rollback: None = None
    requires_mfa: bool = False

class QuickReplyOption(BaseModel):
    title: str
    payload: str

class PresentOptionsAction(BaseModel):
    action: Literal["present_options"]
    payload: Dict[str, List[QuickReplyOption]] = Field(..., example={"options": [{"title": "Track Order", "payload": "Track my recent order"}]})
    rollback: None = None
    requires_mfa: bool = False

AnyAction = Union[
    AddToCartAction, 
    TrackOrderAction, 
    ProductSearchAction, 
    SupportHandoffAction,
    PresentOptionsAction  
]

class Telemetry(BaseModel):
    intent: str
    entities: List[str]
    latency_ms: Optional[int] = None

class NeuralCoreResponse(BaseModel):
    text: str
    action: Optional[AnyAction] = None
    explain: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    telemetry: Telemetry

    model_config = ConfigDict(
        json_serializer=orjson_dumps
    )
