import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.staged_search_service import staged_search
from app.services.ai_nlu_service import CandidateRanker, _build_broad_query
from app.services.neural_core_service import NeuralCoreService,SessionMemory


@pytest.mark.asyncio
@pytest.mark.parametrize('tier',['high_precision_exact','high_precision_ranked','broad_fallback','no_match'])
async def test_real_shared_tiers_preserve_category_and_bounded_identity(tier):
    exact=SimpleNamespace(id=1,name='wireless headphones',price=20)
    other=SimpleNamespace(id=2,name='Audio option',price=10)
    sets={'high_precision_exact':[[exact,exact]],'high_precision_ranked':[[other]],
        'broad_fallback':[[],[other]],'no_match':[[],[]]}
    engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=sets[tier]))
    result=await staged_search(engine,object(),'wireless headphones',category='audio',rank=CandidateRanker(engine).rerank,broaden=lambda q:'headphones')
    assert result.tier==tier and len(result.candidates)<=1
    assert all(call.kwargs['filters']=={'category':'audio'} for call in engine.perform_hybrid_search_pure.call_args_list)
    assert [c.kwargs['limit'] for c in engine.perform_hybrid_search_pure.call_args_list]==[30,5][:engine.perform_hybrid_search_pure.await_count]


@pytest.mark.asyncio
async def test_shared_tier_timeout_cancels_transport():
    cancelled=asyncio.Event()
    async def blocked(*args,**kwargs):
        try:await asyncio.Event().wait()
        finally:cancelled.set()
    with pytest.raises(TimeoutError):
        await staged_search(SimpleNamespace(perform_hybrid_search_pure=blocked),None,'headphones',rank=lambda q,p:p,broaden=_build_broad_query,timeout=.01)
    assert cancelled.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize('injected',[False,True])
async def test_router_target_array_requires_literal_customer_source(injected):
    import json
    service=NeuralCoreService(object(),object());service.is_healthy=True
    service.configuration_error=False
    service._execute_llm_inference=AsyncMock(return_value=json.dumps(dict(intent='PRODUCT_SEARCH',query='Alpha and Beta',search_subject='Alpha',shopping_task='comparison',targets=[{'product_name':'Alpha'},{'product_name':'Invented' if injected else 'Beta'}])))
    decision=await service._analyze_intent('Compare Alpha and Beta',SessionMemory(user_name='Client'))
    if injected:assert decision.intent=='GIFT_DISCOVERY' and decision.targets==[]
    else:assert decision.shopping_task=='comparison' and [t.product_name for t in decision.targets]==['Alpha','Beta']

@pytest.mark.asyncio
async def test_empty_same_query_is_not_repeated():
    retrieve=AsyncMock(return_value=[])
    result=await staged_search(SimpleNamespace(perform_hybrid_search_pure=retrieve),None,'laptop',rank=lambda q,p:p,broaden=lambda q:' LAPTOP ')
    assert result.tier=='no_match' and retrieve.await_count==1
