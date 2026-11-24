"""Literal currency token identity and Arabic decimals, no currency inference."""
from types import SimpleNamespace
import pytest
from app.services.shopping_discovery import ShoppingBrief,catalog_result

@pytest.mark.parametrize('source,amount,currency,accepted',[
 ('under USD 1,000','1','USD',False),('under USD 100,50','100','USD',False),
 ('بحد أقصى ١٬٠٠٠ USD','1','USD',False),
 ('under USDT 100','100','USD',False),('under USDA 100','100','USD',False),
 ('under XEUR 100','100','EUR',False),('under EURX 100','100','EUR',False),
 ('under eur 100','100','EUR',True),('under USD 100','100','USD',True),
 ('under 100 dollars','100','USD',True),('under 100 dollarship','100','USD',False),
 ('بحد أقصى ١٠٠٫٥٠ USD','100.50','USD',True),
 ('بحد أقصى ١٠٠٫٥٠ USD','100','USD',False),
 ('بحد أقصى ١٠٠٫٥٠ USD','50','USD',False),
 ('under USD 100.50','100','USD',False),
 ('under USD 100','100','usd',False),
])
def test_grounded_budget_exact_amount_currency_identity(source,amount,currency,accepted):
    brief=ShoppingBrief(budget=source,budget_max=amount,budget_currency=currency).grounded(source)
    assert (brief.budget_max is not None)==accepted
    assert brief.budget==source
    if accepted:
        card=catalog_result(SimpleNamespace(id=7,name='Atlas',sku='',category='chairs',is_active=True,inventory=3,price=amount,currency=currency,attributes={}))
        assert brief.permits(card)

@pytest.mark.asyncio
@pytest.mark.parametrize('source,amount,currency,accepted',[
 ('under USDT 100','100','USD',False),('under usd 100','100','USD',True),
 ('بحد أقصى ١٠٠٫٥٠ USD','100.50','USD',True),
 ('بحد أقصى ١٠٠٫٥٠ USD','100','USD',False),
])
async def test_actual_router_preserves_unresolved_budget_instead_of_wrong_currency_cap(source,amount,currency,accepted):
    import json
    from unittest.mock import AsyncMock
    from app.services.neural_core_service import NeuralCoreService,SessionMemory
    svc=NeuralCoreService(SimpleNamespace(),SimpleNamespace());svc.is_healthy=True;svc.configuration_error=False
    svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas','search_subject':'Atlas','brief':{'budget':source,'budget_max':amount,'budget_currency':currency}}))
    decision=await svc._analyze_intent('Atlas '+source,SessionMemory(user_name='test'))
    assert decision.brief.budget==source
    assert (decision.brief.budget_max is not None)==accepted
