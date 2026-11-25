import asyncio,json
from copy import deepcopy
from unittest.mock import AsyncMock
import pytest
from tests.test_llm_execution_limits import service,completion

P={'id':7,'name':'Cotton Shirt','price':'24.00','currency':'USD','inventory':3,'is_active':True,'attributes':{'material':'cotton'},'category':'Shirts'}
D={'intro':'Explore this listed option and decide what matters to you.','reasons':[{'product_id':7,'text':'Cotton Shirt lists cotton material; fit details remain unknown.'}],'claims':[{'product_id':7,'field':'name','value':'Cotton Shirt'},{'product_id':7,'field':'spec.material','value':'cotton'}]}
V={k:True for k in ['supported','all_product_mentions_declared','no_unsupported_commercial_claims','fulfills_discovery_task']}

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','reject','invented_id','wrong_field','numeric','missing_name','duplicate','failure','cancel','changed'])
async def test_actual_strict_adapter_preserves_reviewed_prose_or_withholds(mode):
    llm=service();draft=deepcopy(D);verdict=dict(V);products=[deepcopy(P)]
    if mode=='reject':verdict['supported']=False
    if mode=='invented_id':draft['reasons'][0]['product_id']=999
    if mode=='wrong_field':draft['claims'][1]['value']='silk'
    if mode=='numeric':draft['reasons'][0]['text']+=' Save 90 percent.'
    if mode=='missing_name':draft['claims']=draft['claims'][1:]
    if mode=='duplicate':draft['reasons']*=2
    async def respond(**kwargs):
        if mode=='failure':raise ConnectionError('private-failure')
        if mode=='cancel':raise asyncio.CancelledError()
        schema=kwargs['response_format'].get('json_schema',{}).get('name')
        if schema=='GroundingReview':
            if mode=='changed':products[0]['price']='99.00'
            return completion(json.dumps(verdict))
        return completion(json.dumps(draft))
    llm._chat_completion=AsyncMock(side_effect=respond)
    if mode=='cancel':
        with pytest.raises(asyncio.CancelledError):await llm.filter_and_recommend('show me a cotton shirt',products)
        return
    result=await llm.filter_and_recommend('show me a cotton shirt',products)
    if mode=='ok':
        assert result.intro_message==D['intro'] and result.reasoning=={'7':D['reasons'][0]['text']}
        assert result.selected_ids==[7] and llm._chat_completion.await_count==2
    else:
        assert result.selected_ids==[] and result.reasoning=={} and result.confidence_score==0
        assert result.intro_message.startswith('System notice:')

@pytest.mark.asyncio
@pytest.mark.parametrize('patch',[{'inventory':0},{'is_active':False},{'sku':'ADL-DEMO-v1-hidden'}])
async def test_ineligible_complete_cards_do_not_enter_model(patch):
    llm=service();llm._chat_completion=AsyncMock()
    result=await llm.filter_and_recommend('shirt',[{**P,**patch}])
    assert result.selected_ids==[];llm._chat_completion.assert_not_awaited()

@pytest.mark.asyncio
async def test_real_orchestrator_uses_explicit_evidence_and_never_repopulates_rejected_ids():
    from app.services.free_llm_service import SearchStrategy
    llm=service();llm.strategize_search=AsyncMock(return_value=SearchStrategy(is_direct_product_request=True))
    llm.extract_search_terms=AsyncMock(return_value='shirt')
    llm._chat_completion=AsyncMock(side_effect=[completion(json.dumps(D)),completion(json.dumps({**V,'supported':False}))])
    result=await llm.handle_commerce_interaction('cotton shirt',[deepcopy(P)])
    assert result['selected_ids']==[] and result['products']==[] and result['intro']==__import__('app.services.customer_status',fromlist=['STATUSES']).STATUSES['reply_unverified'].text
    assert llm._chat_completion.await_count==2

@pytest.mark.asyncio
async def test_per_product_claims_cannot_borrow_other_cards_numeric_specs():
    llm=service();other={**P,'id':8,'name':'Other Shirt','attributes':{'weight':'90'}}
    draft=deepcopy(D);draft['reasons'][0]['text']='Cotton Shirt weighs 90 grams.'
    draft['reasons'].append({'product_id':8,'text':'Other Shirt lists its weight.'})
    draft['claims'] += [{'product_id':8,'field':'name','value':'Other Shirt'},{'product_id':8,'field':'spec.weight','value':'90'}]
    llm._chat_completion=AsyncMock(return_value=completion(json.dumps(draft)))
    result=await llm.filter_and_recommend('shirt',[P,other])
    assert result.selected_ids==[] and llm._chat_completion.await_count==1

@pytest.mark.asyncio
async def test_review_cannot_miss_undeclared_intro_product_or_unsupported_fixture_claim(monkeypatch):
    monkeypatch.setenv('AIRDELIVER_DEV_FIXTURES','true');monkeypatch.setenv('APP_ENV','development')
    llm=service();draft=deepcopy(D);draft['intro']='Bestselling Cotton Shirt.'
    fixture={**P,'attributes':{'_seed_dataset':'airdeliver-dev-fixtures-v1','material':'cotton'}}
    llm._chat_completion=AsyncMock(return_value=completion(json.dumps(draft)))
    result=await llm.filter_and_recommend('shirt',[fixture])
    assert result.selected_ids==[]
