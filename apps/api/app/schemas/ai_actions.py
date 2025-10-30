# apps/api/app/schemas/ai_actions.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, List, Optional, Union, Dict, Any
import json

def to_utf8(v: Any) -> Any:
    if isinstance(v, str):
        return v.encode('utf-8').decode('utf-8')
    return v

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

AnyAction = Union[AddToCartAction, TrackOrderAction, ProductSearchAction, SupportHandoffAction]

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
        json_serializer=lambda v: json.dumps(v, ensure_ascii=False)
    )
