import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.staged_search_service import staged_search
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,RequestContext,IntentCategory

async def run(rows,**kw):
    return await staged_search(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=rows)),None,kw.pop('query','headphones'),rank=kw.pop('rank',lambda q,p:p),broaden=kw.pop('broaden',lambda q:q),**kw)

@pytest.mark.asyncio
@pytest.mark.parametrize('rows',[None,{},'rows',[SimpleNamespace(id=i+1,name='headphones') for i in range(31)]])
async def test_invalid_or_oversize_transport_result_fails_closed(rows):
    with pytest.raises(ValueError):await run(rows)

@pytest.mark.asyncio
async def test_mapping_rows_and_bad_siblings_have_same_identity_boundary():
    rows=[{'id':1,'name':'headphones','price':'NaN'},None,{'id':True,'name':'headphones'}, {'id':1,'name':'changed duplicate'}]
    result=await run(rows)
    assert result.tier=='high_precision_exact' and result.candidates==(rows[0],)

@pytest.mark.asyncio
async def test_ranker_cannot_create_or_replace_retrieved_candidate():
    row=SimpleNamespace(id=1,name='audio option',price=10)
    result=await run([row],rank=lambda q,p:[SimpleNamespace(id=1,name='injected replacement'),SimpleNamespace(id=2,name='invented')])
    assert result.candidates==(row,)

@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs',[{'query':None},{'timeout':float('nan')},{'timeout':True},{'category':{}},{'category':'x'*129},{'broaden':lambda q:[]},{'broaden':lambda q:'x'*257}])
async def test_query_category_deadline_and_broadener_boundaries(kwargs):
    with pytest.raises(ValueError):await run([],**kwargs)

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[TimeoutError(),ConnectionError(),asyncio.CancelledError()])
async def test_original_universal_search_never_publishes_partial_outage(failure):
    svc=AINLUService(object(),SimpleNamespace(),object(),SimpleNamespace(),SimpleNamespace())
    svc._execute_strategic_search=AsyncMock(side_effect=[[SimpleNamespace(id=1,name='desk')],failure])
    request=svc._parse_incoming_message({'user_id':17,'message':'desk and chair'})
    intent=CommerceIntentPayload(category=IntentCategory.SPECIFIC_SEARCH,is_chitchat=False,target_products=[{'product_name':'desk'},{'product_name':'chair'}])
    if isinstance(failure,asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):await svc._execute_universal_search(request=request,intent_payload=intent,ctx=RequestContext(17,'test',0))
    else:
        assert await svc._execute_universal_search(request=request,intent_payload=intent,ctx=RequestContext(17,'test',0))==([],True,'')

@pytest.mark.asyncio
async def test_broad_transport_cancellation_releases_operation():
    finished=asyncio.Event();count=0
    async def retrieve(*a,**k):
        nonlocal count
        count+=1
        if count==1:return []
        try:await asyncio.Event().wait()
        finally:finished.set()
    task=asyncio.create_task(staged_search(SimpleNamespace(perform_hybrid_search_pure=retrieve),None,'wireless headphones',rank=lambda q,p:p,broaden=lambda q:'headphones'))
    while count<2:await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert finished.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize('queries',['desk',[None],['x']*4])
async def test_original_strategy_rejects_ambiguous_query_container(queries):
    svc=AINLUService(object(),SimpleNamespace(),object(),SimpleNamespace(),SimpleNamespace())
    with pytest.raises(ValueError):await svc._execute_strategic_search(SimpleNamespace(search_queries=queries),17,'desk')
