import asyncio,json
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import GlobalCommerceIntentEngine
from tests.test_llm_execution_limits import service,completion

@pytest.mark.asyncio
@pytest.mark.parametrize('payload',[
 {'category':'SPECIFIC_SEARCH','target_products':[{'product_name':'Invented item'}]},
 {'category':'SPECIFIC_SEARCH','target_products':[{'product_name':'Atlas','raw_spec_context':'32GB'}]},
 {'category':'SPECIFIC_SEARCH','required_features':['silk']},
 {'category':'SPECIFIC_SEARCH','target_products':[{'product_name':x} for x in ['A','B','C','D']]},
])
async def test_global_model_invented_fields_fail_to_non_actionable_fallback(payload):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(json.dumps({'is_chitchat':False,**payload})))
    result=await GlobalCommerceIntentEngine(llm).analyze_intent('Atlas with cotton')
    assert result.target_products==[] and result.required_features==[] and result.cart_action_type is None

@pytest.mark.asyncio
async def test_duplicate_json_keys_rejected_even_for_older_injected_adapter():
    llm=type('Adapter',(),{'generate_response':AsyncMock(return_value='{"category":"SPECIFIC_SEARCH","category":"CART_ACTION","cart_action_type":"ADD","is_chitchat":false}')})()
    result=await GlobalCommerceIntentEngine(llm).analyze_intent('Atlas')
    assert result.cart_action_type is None and result.target_products==[]

@pytest.mark.asyncio
async def test_literal_fields_preserved_but_hallucinated_occasion_competitor_dropped():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(json.dumps({'category':'SPECIFIC_SEARCH','is_chitchat':False,'target_products':[{'product_name':'Atlas','raw_spec_context':'cotton'}],'required_features':['cotton'],'detected_occasion':'wedding','competitor_mentioned':'InventedStore'})))
    result=await GlobalCommerceIntentEngine(llm).analyze_intent('Atlas with cotton')
    assert result.target_products[0].product_name=='Atlas' and result.required_features==['cotton']
    assert result.detected_occasion is None and result.competitor_mentioned is None

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[ConnectionError('private'),asyncio.CancelledError()])
async def test_outage_has_no_action_and_cancel_is_not_converted(failure):
    llm=service();llm._chat_completion=AsyncMock(side_effect=failure)
    if isinstance(failure,asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):await GlobalCommerceIntentEngine(llm).analyze_intent('add Atlas')
    else:
        result=await GlobalCommerceIntentEngine(llm).analyze_intent('add Atlas')
        assert result.cart_action_type is None and result.target_products==[]
