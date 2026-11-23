"""Shared sales presentation boundary for HTTP and optional event adapters.

This service never mutates a cart, starts checkout, retrieves private context or
calls providers on import. Callers supply a bounded current-catalog evidence set
and the existing provider adapter. Optional worker/UI entry points can adopt it
without putting model availability on a cart-commit critical path.
"""
from dataclasses import dataclass,field
from typing import Awaitable,Callable,Literal
import logging
from copy import deepcopy
from app.schemas.ai_actions import CatalogResult,NeuralCoreResponse
from app.services.shopping_copy import write_shopping_copy
from app.services.shopping_discovery import ShoppingBrief

logger=logging.getLogger('airdeliver.sales_response')
Infer=Callable[[list[dict[str,str]]],Awaitable[str]]


@dataclass(frozen=True)
class SalesResponseRequest:
    message: str
    products: tuple[CatalogResult,...]
    brief: ShoppingBrief
    mode: Literal['catalog_results','clarification','conversation']
    intent: str
    evidence: dict=field(default_factory=dict)

    def __post_init__(self):
        if len(self.message)>10000 or len(self.products)>5:
            raise ValueError('Sales request exceeds boundary')
        identities=[p.id for p in self.products]
        if len(set(identities))!=len(identities):raise ValueError('Duplicate sales identity')
        if self.mode in {'clarification','conversation'} and self.products:
            raise ValueError('Non-catalog response cannot recommend products')
        if not self.intent or len(self.intent)>128:raise ValueError('Invalid sales intent')


class SalesResponseService:
    def __init__(self,infer: Infer,*,provider_ready: bool,timeout: float):
        if timeout<=0 or timeout>30:raise ValueError('Sales deadline must be bounded')
        self.infer=infer;self.provider_ready=provider_ready;self.timeout=timeout

    async def respond(self,request: SalesResponseRequest) -> NeuralCoreResponse:
        # Freeze a per-request snapshot. A caller holding mutable ORM/card objects
        # cannot alter evidence while writer/review network awaits are in flight.
        cards=[p.model_copy(deep=True) for p in request.products]
        brief=request.brief.model_copy(deep=True)
        try:
            if not self.provider_ready:raise RuntimeError('provider_unavailable')
            text=await write_shopping_copy(self.infer,request.message,cards,brief.model_dump(),
                request.mode,self.timeout,deepcopy(request.evidence))
            kind=request.mode
        except Exception as exc:
            logger.warning('sales_response.copy_withheld',extra={'error_type':type(exc).__name__,'intent':request.intent})
            text='System notice: a grounded shopping reply could not be generated. No product is reserved and no merchant availability has been verified. Please try again or browse the catalog.'
            kind='system_notice';cards=[]
        return NeuralCoreResponse(text=text,products=cards,response_kind=kind,
            confidence=0.5 if kind!='system_notice' else 0.0,
            explain='Model-authored copy with structured evidence and independent grounding review',
            telemetry={'intent':request.intent,'entities':[],'turn':0})
