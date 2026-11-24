import json
from unittest.mock import AsyncMock
import pytest
from app.services.neural_core_service import NeuralCoreService,SessionMemory

@pytest.mark.asyncio
@pytest.mark.parametrize('signal,expected',[('too expensive','price_objection'),('invented distress','browse'),(None,'browse'),('','browse')])
async def test_shopping_strategy_requires_current_customer_signal(signal,expected):
    svc=NeuralCoreService(object(),object());svc.is_healthy=True;svc.configuration_error=False
    svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'headphones','search_subject':'headphones','advice_goal':'price_objection','customer_signal':signal,'targets':[{'product_name':'headphones'}]}))
    decision=await svc._analyze_intent('headphones are too expensive',SessionMemory(user_name='Client'))
    assert decision.advice_goal==expected
