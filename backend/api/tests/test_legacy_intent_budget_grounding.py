"""Legacy intent payload must not keep a budget the customer never stated."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import GlobalCommerceIntentEngine

async def run(message,budget,history=''):
    infer=AsyncMock(return_value=json.dumps({'category':'SPECIFIC_SEARCH','target_products':[{'product_name':'Atlas'}],'is_chitchat':False,'budget_max':budget}))
    return await GlobalCommerceIntentEngine(SimpleNamespace(generate_response_strict=infer)).analyze_intent(message,history) if history else await GlobalCommerceIntentEngine(SimpleNamespace(generate_response_strict=infer)).analyze_intent(message)

@pytest.mark.asyncio
@pytest.mark.parametrize('budget',[999,-1,0,50.5])
async def test_invented_budget_is_dropped(budget):
    assert (await run('Show Atlas headphones',budget)).budget_max is None

@pytest.mark.asyncio
@pytest.mark.parametrize('message,budget',[
 ('Atlas headphones under 200',200),('Atlas headphones max $1,500',1500),('Atlas headphones under 2k',2000),('Atlas headphones around 99.5 dollars',99.5)])
async def test_stated_budget_is_kept(message,budget):
    assert (await run(message,budget)).budget_max==budget

@pytest.mark.asyncio
async def test_unrelated_number_does_not_ground_budget():
    assert (await run('Show Atlas headphones model 300',999)).budget_max is None
