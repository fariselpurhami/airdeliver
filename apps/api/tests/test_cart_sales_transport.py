"""Provider wire and cart mutation separation, no external provider calls."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import FreeLLMService, StructuredOutputError
from app.services.ai_cart_service import AICartService
from tests.test_ai_cart_service import FakeCache, FakeDB, make_product


@pytest.mark.asyncio
async def test_sales_transport_uses_existing_deadline_admission_adapter_and_strict_json():
    svc=object.__new__(FreeLLMService);svc.__init__()
    svc._chat_completion=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=' {"text":"reply"} '))]))
    messages=[{'role':'system','content':'rules'},{'role':'user','content':'evidence'}]
    assert await svc.infer_sales_json(messages)=='{"text":"reply"}'
    wire=svc._chat_completion.await_args.kwargs
    assert wire['messages']==messages and wire['response_format']=={'type':'json_object'}
    assert wire['model']==svc.models.brain_model and wire['max_tokens']==1200
    svc._chat_completion=AsyncMock(side_effect=ConnectionError('offline'))
    with pytest.raises(ConnectionError):await svc.infer_sales_json(messages)
    svc._chat_completion=AsyncMock(return_value=SimpleNamespace(choices=[]))
    with pytest.raises(StructuredOutputError):await svc.infer_sales_json(messages)


@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['added','removed'])
async def test_injected_worker_ai_never_runs_model_or_search_on_mutation_path(operation):
    cache=FakeCache({'items':[{'product_id':7,'name':'Shoes','quantity':1,'price':'19.99'}]} if operation=='removed' else None)
    broker=SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True)))
    engine=SimpleNamespace(generate_perfect_bundle=AsyncMock(),find_genius_alternatives=AsyncMock())
    llm=SimpleNamespace(generate_response=AsyncMock(),infer_sales_json=AsyncMock())
    svc=AICartService(FakeDB(make_product()),cache,broker,engine,llm)
    await (svc.handle_add_to_cart if operation=='added' else svc.handle_remove_from_cart)({'user_id':5,'product_id':7})
    engine.generate_perfect_bundle.assert_not_awaited();engine.find_genius_alternatives.assert_not_awaited()
    llm.generate_response.assert_not_awaited();llm.infer_sales_json.assert_not_awaited()
    assert any(c.args[0].get('operation')==operation for c in broker.publish.call_args_list)
    assert any(p.get('type')=='success_text' for _,p in cache.published)
