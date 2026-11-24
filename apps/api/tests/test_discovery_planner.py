import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.discovery_planner import plan_setup
from app.services.neural_core_service import NeuralCoreService,SessionMemory,RouterDecision
from app.services.shopping_discovery import ShoppingBrief

@pytest.mark.asyncio
async def test_setup_plan_is_generic_reviewed_and_bounded():
    infer=AsyncMock(side_effect=[json.dumps({'components':['desk','chair','lamp']}),json.dumps({'appropriate':True,'no_invented_products':True})])
    assert await plan_setup(infer,'build a home office setup')==['desk','chair','lamp']
    assert infer.await_count==2

@pytest.mark.asyncio
@pytest.mark.parametrize('components,accepted',[(['invented model'],False),([],True),(['desk','chair','lamp','rug'],True)])
async def test_invalid_or_rejected_component_plan_does_not_search(components,accepted):
    infer=AsyncMock(side_effect=[json.dumps({'components':components}),json.dumps({'appropriate':accepted,'no_invented_products':True})])
    with pytest.raises(ValueError):await plan_setup(infer,'setup')

@pytest.mark.asyncio
async def test_http_service_setup_dispatch_reuses_staged_component_search():
    svc=NeuralCoreService(SimpleNamespace(),object())
    svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps({'components':['desk','chair']}),json.dumps({'appropriate':True,'no_invented_products':True})])
    svc._handle_staged_product_search=AsyncMock(return_value='reviewed-result')
    assert await svc._handle_setup_discovery(object(),'home office setup',ShoppingBrief())=='reviewed-result'
    decision=svc._handle_staged_product_search.await_args.args[1]
    assert decision.shopping_task=='setup' and [t.product_name for t in decision.targets]==['desk','chair']

@pytest.mark.asyncio
async def test_visual_identity_enriches_retrieval_without_becoming_product_evidence(monkeypatch):
    from app.services.free_llm_service import FreeLLMService
    identify=AsyncMock(return_value='visible product keywords')
    monkeypatch.setattr(FreeLLMService,'analyze_product_image',identify)
    engine=SimpleNamespace(search_by_image_vector=AsyncMock(return_value=[SimpleNamespace(id=1)]),perform_hybrid_search_pure=AsyncMock(return_value=[SimpleNamespace(id=2)]))
    svc=NeuralCoreService(engine,object());svc._catalog_response=AsyncMock(return_value='reviewed-result')
    assert await svc._handle_visual_search('base64-test','find this',object())=='reviewed-result'
    assert [p.id for p in svc._catalog_response.await_args.args[1]]==[1,2]
    assert svc._catalog_response.await_args.args[3]=='find this'
    identify.assert_awaited_once()
