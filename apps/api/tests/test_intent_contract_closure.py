import json
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app.services.ai_nlu_service import CommerceIntentPayload
from app.services.neural_core_service import NeuralCoreService,SessionMemory
from tests.test_neural_core_visual import FakeCache

@pytest.mark.parametrize('field,value',[('product_name',42),('product_name',True),('domain_hint',[]),('raw_spec_context',{})])
def test_original_target_fields_are_not_stringified(field,value):
    with pytest.raises(ValidationError):CommerceIntentPayload(category='SPECIFIC_SEARCH',is_chitchat=False,target_products=[{'product_name':'Atlas',field:value}])

@pytest.mark.asyncio
@pytest.mark.parametrize('grounded',[True,False])
async def test_ordinary_sentiment_and_competitor_are_literal_current_metadata(grounded):
    service=NeuralCoreService(object(),FakeCache());service.is_healthy=True
    message='I am frustrated with Atlas headphones from OtherStore'
    service._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas headphones','search_subject':'Atlas headphones','targets':[{'product_name':'Atlas headphones'},{'product_name':'atlas headphones'}],
        'sentiment':'FRUSTRATED','sentiment_evidence':'frustrated' if grounded else 'angry',
        'competitor_mentioned':'OtherStore' if grounded else 'InventedStore'}))
    decision=await service._analyze_intent(message,SessionMemory(user_name='test'))
    assert decision.sentiment==('FRUSTRATED' if grounded else 'NEUTRAL')
    assert decision.competitor_mentioned==('OtherStore' if grounded else None)
    assert len(decision.targets)==1
