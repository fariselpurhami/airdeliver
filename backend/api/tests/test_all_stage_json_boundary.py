"""Shared actual inference return boundary, not provider semantic acceptance."""
import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import BaseModel
from app.services.structured_output import infer_schema
from app.services.neural_core_service import NeuralCoreService,SessionMemory

class Verdict(BaseModel):
    grounded:bool

@pytest.mark.asyncio
@pytest.mark.parametrize('raw',[
 '{"grounded":false,"grounded":true}',
 '{"details":{"a":1,"a":2},"grounded":true}',
 '{"grounded":true,"score":NaN}',
 '{"grounded":true,"score":Infinity}',
 '[{"grounded":true}]','null','{"grounded":true}'+(' '*32768),
])
@pytest.mark.parametrize('native',[True,False])
async def test_shared_return_boundary_rejects_ambiguous_object(raw,native):
    class Owner:
        async def _execute_schema_inference(self,messages,model):return raw
        async def infer(self,messages):raise AssertionError('Wrong adapter')
    call=Owner().infer if native else AsyncMock(return_value=raw)
    with pytest.raises(ValueError):await infer_schema(call,[],Verdict)

@pytest.mark.asyncio
@pytest.mark.parametrize('native',[True,False])
async def test_original_valid_json_is_preserved_for_domain_parser(native):
    raw=' {"grounded":true} '
    class Owner:
        async def _execute_schema_inference(self,messages,model):return raw
        async def infer(self,messages):raise AssertionError('Wrong adapter')
    call=Owner().infer if native else AsyncMock(return_value=raw)
    assert await infer_schema(call,[],Verdict)==raw

@pytest.mark.asyncio
async def test_router_does_not_accept_last_duplicate_cart_intent():
    service=object.__new__(NeuralCoreService);service.configuration_error=False;service.is_healthy=True
    service._execute_llm_inference=AsyncMock(return_value='{"intent":"SOCIAL_CHAT","intent":"CART_CLEAR"}')
    decision=await service._analyze_intent('clear my cart',SessionMemory(user_name='test'))
    assert decision.intent=='SOCIAL_CHAT'
    assert 'could not validate' in decision.social_reply

@pytest.mark.asyncio
async def test_shared_boundary_never_swallows_cancellation():
    call=AsyncMock(side_effect=asyncio.CancelledError)
    with pytest.raises(asyncio.CancelledError):await infer_schema(call,[],Verdict)

@pytest.mark.asyncio
@pytest.mark.parametrize('values,stage',[
 (['{"text":"a","text":"b","product_ids":[],"claims":[]}'],'writer_schema'),
 ([json.dumps({'text':'Compare the cards','product_ids':[],'claims':[]}),'{"supported":false,"supported":true}'],'review_schema'),
])
async def test_copy_reports_invalid_return_as_schema_not_provider_failure(values,stage):
    from app.services.shopping_copy import write_shopping_copy,ShoppingCopyError
    with pytest.raises(ShoppingCopyError) as error:
        await write_shopping_copy(AsyncMock(side_effect=values),'jewelry',[],{},'catalog_results',1)
    assert error.value.stage==stage
