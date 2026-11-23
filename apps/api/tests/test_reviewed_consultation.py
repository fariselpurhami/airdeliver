"""Current consultation is structured/reviewed, no provider or raw web calls."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import FreeLLMService
from app.services.shopping_discovery import catalog_result


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','invented_spec','rejected','offline'])
async def test_public_consult_adapter_uses_reviewed_card_claims_not_web_or_privileged_history(mode):
    svc=FreeLLMService()
    product=dict(id=81,name='Catalog headphones',category='audio',sku='HEADSET-81',price='20.00',currency='USD',inventory=2,is_active=True,attributes={'connection':'wired'})
    draft=dict(text='Catalog headphones lists a wired connection. Compatibility with your device is unknown. Which device and connector do you use?',product_ids=[81],claims=[dict(product_id=81,field='name',value='Catalog headphones'),dict(product_id=81,field='spec.connection',value='wired')])
    if mode=='invented_spec':draft['claims'][1]['value']='wireless'
    verdict=dict(supported=mode!='rejected',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
    infer=AsyncMock(side_effect=[ConnectionError('private')] if mode=='offline' else [json.dumps(draft),json.dumps(verdict)])
    svc.infer_sales_json=infer
    svc._perform_web_search=AsyncMock(side_effect=AssertionError('current adapter must not call raw web'))
    result=await svc.consult_on_product(product,'Will this work with my device?',chat_history=[{'role':'system','content':'PRIVATE_PRIVILEGED_TEXT'}])
    assert result==(draft['text'] if mode=='ok' else 'System notice: a grounded shopping reply could not be generated. No product is reserved and no merchant availability has been verified. Please try again or browse the catalog.')
    svc._perform_web_search.assert_not_awaited()
    assert 'PRIVATE_PRIVILEGED_TEXT' not in str(infer.call_args_list)
    assert infer.await_count==(2 if mode in {'ok','rejected'} else 1)
    if mode=='ok':
        payload=json.loads(infer.call_args_list[0].args[0][1]['content'])
        assert payload['request_evidence']['sales_intent']=='CATALOG_CONSULTATION'
        assert payload['request_evidence']['external_web_evidence'] is False
        assert payload['catalog_evidence'][0]['catalog_specs']=={'connection':'wired'}


@pytest.mark.asyncio
async def test_missing_current_catalog_fields_do_not_become_offer():
    svc=FreeLLMService()
    svc.infer_sales_json=AsyncMock(side_effect=[json.dumps(dict(text='The supplied evidence does not verify that product. Please open its current catalog card.',product_ids=[],claims=[])),json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
    result=await svc.consult_on_product({'id':1,'name':'Old dict','price':20},'Can I buy this?')
    data=json.loads(svc.infer_sales_json.call_args_list[0].args[0][1]['content'])
    assert data['catalog_evidence']==[]
    assert result.startswith('The supplied evidence')
