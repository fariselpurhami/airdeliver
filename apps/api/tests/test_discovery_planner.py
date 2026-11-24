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

@pytest.mark.asyncio
async def test_setup_recent_customer_context_is_bounded_separate_data():
    infer=AsyncMock(side_effect=[json.dumps({'components':['desk']}),json.dumps({'appropriate':True,'no_invented_products':True})])
    await plan_setup(infer,'now build setup',customer_context=tuple(str(i) for i in range(8)))
    for call in infer.await_args_list:
        payload=json.loads(call.args[0][1]['content'])
        assert payload['customer_only_recent_context']==['3','4','5','6','7']

@pytest.mark.asyncio
async def test_visual_publication_keeps_prior_hard_brief_and_customer_context(monkeypatch):
    from app.services.neural_core_service import _customer_turn_context
    from app.services.free_llm_service import FreeLLMService
    monkeypatch.setattr(FreeLLMService,'analyze_product_image',AsyncMock(return_value='generic'))
    svc=NeuralCoreService(SimpleNamespace(search_by_image_vector=AsyncMock(return_value=[])),object())
    svc._catalog_response=AsyncMock(return_value='verified')
    brief=ShoppingBrief(required_features=['16GB RAM'])
    token=_customer_turn_context.set(('customer headphones request',))
    try:
        assert await svc._handle_visual_search('image','this one',object(),brief=brief)=='verified'
        kwargs=svc._catalog_response.await_args.kwargs
        assert kwargs['brief']==brief
        assert kwargs['search_evidence']['customer_only_recent_context']==['customer headphones request']
    finally:_customer_turn_context.reset(token)

@pytest.mark.asyncio
async def test_component_requirements_are_literal_and_reviewed_not_unrelated_features():
    infer=AsyncMock(side_effect=[json.dumps({'components':['laptop','chair'],'component_requirements':{'laptop':['16GB RAM']}}),json.dumps({'appropriate':True,'no_invented_products':True})])
    plan=await plan_setup(infer,'setup with laptop16GB RAM and chair',detailed=True)
    assert plan.component_requirements=={'laptop':['16GB RAM']}
    infer=AsyncMock(return_value=json.dumps({'components':['laptop'],'component_requirements':{'chair':['invented']}}))
    with pytest.raises(ValueError):await plan_setup(infer,'laptop16GB RAM',detailed=True)

@pytest.mark.asyncio
async def test_scoped_assignment_rejection_withholds_search():
    svc=NeuralCoreService(SimpleNamespace(),object())
    svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps({'components':['desk','chair'],'component_requirements':{'chair':['120cm']}}),json.dumps({'appropriate':False,'no_invented_products':True})])
    svc._handle_staged_product_search=AsyncMock()
    response=await svc._handle_setup_discovery(object(),'desk120cm and chair',ShoppingBrief(required_features=['120cm']))
    svc._handle_staged_product_search.assert_not_awaited()
    assert response.explain=='Setup plan unavailable'

@pytest.mark.asyncio
async def test_setup_scopes_survive_new_service_and_omitted_assignment():
    memory=SessionMemory(user_name='Fixture',shopping_brief=ShoppingBrief(required_features=['120cm']))
    first=NeuralCoreService(SimpleNamespace(),object())
    first._execute_llm_inference=AsyncMock(side_effect=[json.dumps({'components':['desk','chair'],'component_requirements':{'desk':['120cm']}}),json.dumps({'appropriate':True,'no_invented_products':True})])
    result=SimpleNamespace(response_kind='text')
    first._handle_staged_product_search=AsyncMock(return_value=result)
    await first._handle_setup_discovery(object(),'desk120cm and chair setup',memory.shopping_brief,memory=memory)
    restored=SessionMemory.model_validate_json(memory.model_dump_json())
    second=NeuralCoreService(SimpleNamespace(),object())
    second._execute_llm_inference=AsyncMock(side_effect=[json.dumps({'components':['desk','chair']}),json.dumps({'appropriate':True,'no_invented_products':True})])
    second._handle_staged_product_search=AsyncMock(return_value=result)
    await second._handle_setup_discovery(object(),'show more setup options',restored.shopping_brief,memory=restored)
    _,decision,brief,_=second._handle_staged_product_search.await_args.args
    assert decision.targets[0].required_features==['120cm'] and decision.targets[1].required_features==[]
    assert brief.required_features==[] and restored.setup_requirements=={'desk':['120cm']}

@pytest.mark.asyncio
async def test_prior_component_identity_cannot_silently_drop_scope():
    memory=SessionMemory(user_name='Fixture',setup_requirements={'desk':['120cm']})
    svc=NeuralCoreService(SimpleNamespace(),object())
    svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps({'components':['table','chair']}),json.dumps({'appropriate':True,'no_invented_products':True})])
    svc._handle_staged_product_search=AsyncMock()
    result=await svc._handle_setup_discovery(object(),'more setup options',ShoppingBrief(),memory=memory)
    svc._handle_staged_product_search.assert_not_awaited()
    assert result.explain=='Setup plan unavailable' and memory.setup_requirements=={'desk':['120cm']}


@pytest.mark.asyncio
async def test_setup_exclusion_unknown_or_nonliteral_scope_rejected():
    infer=AsyncMock(return_value=json.dumps({'components':['desk'],'component_exclusions':{'chair':['invented']}}))
    with pytest.raises(ValueError):await plan_setup(infer,'desk not red',detailed=True)
