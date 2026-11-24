# apps/api/app/schemas/ai_actions.py

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union, Annotated

import orjson
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr
from pydantic import field_validator


def _orjson_dumps(value: Any, *, default: Any) -> str:
    return orjson.dumps(value, default=default).decode("utf-8")


class SchemaBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        validate_assignment=True,
        use_enum_values=True,
        frozen=False,
        json_schema_extra={"additionalProperties": False},
        ser_json_timedelta="iso8601",
        ser_json_bytes="utf8",
        json_dumps=_orjson_dumps,
    )


class CartActionPayload(SchemaBaseModel):
    user_id: StrictStr = Field(..., alias="userId", min_length=1, max_length=128)
    sku: StrictStr = Field(..., min_length=1, max_length=128)
    qty: StrictInt = Field(..., ge=1, le=9999)

    @field_validator("user_id", "sku")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class CartRemoveRollback(SchemaBaseModel):
    action: Literal["cart_remove"] = "cart_remove"
    payload: CartActionPayload


class AddToCartAction(SchemaBaseModel):
    action: Literal["add_to_cart"] = "add_to_cart"
    payload: CartActionPayload
    rollback: CartRemoveRollback
    requires_mfa: StrictBool = False

    @field_validator("rollback")
    @classmethod
    def validate_rollback_matches_payload(
        cls,
        rollback: CartRemoveRollback,
        info: Any,
    ) -> CartRemoveRollback:
        payload = info.data.get("payload")
        if payload is not None and rollback.payload != payload:
            raise ValueError("rollback payload must exactly match the forward action payload")
        return rollback


class TrackOrderPayload(SchemaBaseModel):
    order_id: StrictStr = Field(..., alias="orderId", min_length=1, max_length=128)

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("orderId must not be blank")
        return normalized


class TrackOrderAction(SchemaBaseModel):
    action: Literal["track_order"] = "track_order"
    payload: TrackOrderPayload
    rollback: None = None
    requires_mfa: StrictBool = False


class ProductSearchPayload(SchemaBaseModel):
    query: StrictStr = Field(..., min_length=1, max_length=512)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class ProductSearchAction(SchemaBaseModel):
    action: Literal["product_search"] = "product_search"
    payload: ProductSearchPayload
    rollback: None = None
    requires_mfa: StrictBool = False


class SupportHandoffPayload(SchemaBaseModel):
    reason: Optional[StrictStr] = Field(default=None, min_length=1, max_length=256)
    conversation_id: Optional[StrictStr] = Field(
        default=None,
        alias="conversationId",
        min_length=1,
        max_length=128,
    )
    metadata: Optional[Dict[StrictStr, Any]] = None

    @field_validator("reason", "conversation_id")
    @classmethod
    def normalize_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("optional string fields must not be blank when provided")
        return normalized


class SupportHandoffAction(SchemaBaseModel):
    action: Literal["initiate_support_handoff"] = "initiate_support_handoff"
    payload: Optional[SupportHandoffPayload] = None
    rollback: None = None
    requires_mfa: StrictBool = False


class QuickReplyOption(SchemaBaseModel):
    title: StrictStr = Field(..., min_length=1, max_length=80)
    payload: StrictStr = Field(..., min_length=1, max_length=256)

    @field_validator("title", "payload")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class PresentOptionsPayload(SchemaBaseModel):
    options: List[QuickReplyOption] = Field(
        ...,
        min_length=1,
        max_length=10,
        examples=[
            {
                "options": [
                    {
                        "title": "Track Order",
                        "payload": "Track my recent order",
                    }
                ]
            }
        ],
    )

    @field_validator("options")
    @classmethod
    def validate_unique_option_payloads(
        cls,
        options: List[QuickReplyOption],
    ) -> List[QuickReplyOption]:
        payloads = [option.payload for option in options]
        if len(payloads) != len(set(payloads)):
            raise ValueError("option payload values must be unique")
        return options


class PresentOptionsAction(SchemaBaseModel):
    action: Literal["present_options"] = "present_options"
    payload: PresentOptionsPayload
    rollback: None = None
    requires_mfa: StrictBool = False


class CartReviewPayload(SchemaBaseModel):
    review_id: StrictStr = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    product_id: StrictInt = Field(gt=0, le=2147483647)
    product_name: StrictStr = Field(min_length=1, max_length=512)
    operation: Literal["add", "remove"]
    quantity: StrictInt = Field(ge=1, le=99)
    price: StrictStr = Field(min_length=1, max_length=32)
    currency: Literal["USD"] = "USD"


class CartReviewAction(SchemaBaseModel):
    action: Literal["review_cart_change"] = "review_cart_change"
    payload: CartReviewPayload
    rollback: None = None
    requires_mfa: StrictBool = False


class CartLifecycleReviewPayload(SchemaBaseModel):
    review_id: StrictStr = Field(pattern=r'^[0-9a-f-]{36}$')
    operation: Literal['clear','save']
    item_count: StrictInt = Field(ge=1)

class CartLifecycleReviewAction(SchemaBaseModel):
    action: Literal['review_cart_lifecycle'] = 'review_cart_lifecycle'
    payload: CartLifecycleReviewPayload
    rollback: None = None
    requires_mfa: StrictBool = False


AnyAction = Annotated[
    Union[
        AddToCartAction,
        CartReviewAction,
        CartLifecycleReviewAction,
        TrackOrderAction,
        ProductSearchAction,
        SupportHandoffAction,
        PresentOptionsAction,
    ],
    Field(discriminator="action"),
]


class Telemetry(SchemaBaseModel):
    intent: StrictStr = Field(..., min_length=1, max_length=128)
    entities: List[StrictStr] = Field(default_factory=list, max_length=100)
    latency_ms: Optional[StrictInt] = Field(default=None, ge=0, le=3_600_000)
    turn: Optional[StrictInt] = Field(default=0, ge=0)
    correlation_id: Optional[StrictStr] = Field(default=None, max_length=128)
    fault_domain: Optional[StrictStr] = Field(default=None, max_length=128)
    user_id: Optional[StrictInt] = None

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("intent must not be blank")
        return normalized

    @field_validator("entities")
    @classmethod
    def normalize_entities(cls, values: List[str]) -> List[str]:
        normalized_values: List[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized:
                raise ValueError("entities must not contain blank values")
            normalized_values.append(normalized)
        return normalized_values


class CatalogResult(SchemaBaseModel):
    id: StrictInt = Field(gt=0,le=2147483647)
    name: StrictStr = Field(min_length=1,max_length=255)
    sku: StrictStr = Field(default='',max_length=128)
    category: StrictStr = Field(default='uncategorized',max_length=128)
    price: Optional[StrictStr] = None
    currency: Optional[StrictStr] = None
    price_status: Literal['listed','unknown']
    image: Optional[StrictStr] = None
    attributes: Dict[str,str] = Field(default_factory=dict)
    catalog_specs: Dict[str,str] = Field(default_factory=dict)
    relation: Literal['candidate','requested','alternative'] = 'candidate'
    evidence_kind: Literal['seeded_demo','local_catalog']
    stock_status: Literal['demo','local_in_stock','local_out_of_stock','unverified']
    availability_note: StrictStr


class NeuralCoreResponse(SchemaBaseModel):
    text: StrictStr = Field(..., min_length=1, max_length=10_000)
    action: Optional[AnyAction] = None
    products: List[CatalogResult] = Field(default_factory=list,max_length=5)
    response_kind: Literal["text","catalog_results","clarification","system_notice","conversation"] = "text"
    explain: StrictStr = Field(..., min_length=1, max_length=10_000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    telemetry: Optional[Telemetry] = None

    @field_validator("text", "explain")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    def enrich_telemetry(self, **kwargs) -> "NeuralCoreResponse":
        """Safely merges new telemetry data with validation."""
        if not self.telemetry:
            self.telemetry = Telemetry(**kwargs)
        else:
            current_data = self.telemetry.model_dump()
            current_data.update(kwargs)
            self.telemetry = Telemetry.model_validate(current_data)
        return self
