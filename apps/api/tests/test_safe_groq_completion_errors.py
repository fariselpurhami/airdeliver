import json
from types import SimpleNamespace
import httpx
import pytest
from groq import BadRequestError
from scripts.groq_error_metadata import safe_error_metadata
from scripts.accept_dev_cart import Ledger, make_bounded_service


def error(body):
    return BadRequestError('sensitive-message', response=httpx.Response(400,
        request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
        headers={'x-request-id':'req_abcdefgh1234','content-type':'application/json'}),body=body)


@pytest.mark.parametrize('nested',[True,False])
def test_actual_sdk_error_extracts_only_fixed_fields(nested):
    body={'type':'invalid_request_error','code':'json_validate_failed',
          'param':'response_format','message':'sensitive-message','failed_generation':'sensitive-output'}
    row=safe_error_metadata(error({'error':body} if nested else body))
    assert row['http_status']==400 and row['provider_code']=='json_validate_failed'
    assert row['provider_error_type']=='invalid_request_error'
    assert row['provider_param']=='response_format' and row['request_id']=='req_abcdefgh1234'
    assert 'sensitive' not in json.dumps(row)


@pytest.mark.parametrize('body',[None,'sensitive-message',{'error':[]},
    {'code':'sensitive-code','param':'sensitive-param','type':'sensitive-type'},
    {'code':{},'param':[],'type':False}])
def test_arbitrary_payload_is_not_echoed_or_stringified(body):
    row=safe_error_metadata(error(body))
    assert row['provider_code']==row['provider_param']==row['provider_error_type']=='not_in_allowlist'
    assert 'sensitive' not in json.dumps(row)


@pytest.mark.asyncio
async def test_production_recommendation_wire_and_safe_failure(tmp_path, monkeypatch):
    from app.services.free_llm_service import FreeLLMService
    monkeypatch.setattr(FreeLLMService, "_instance", None)
    service=FreeLLMService();sent=[]
    saved={name:getattr(service,name) for name in ('_chat_completion','_get_client','_client','limits')}
    async def create(**kwargs):
        sent.append(kwargs)
        raise error({'error':{'code':'json_validate_failed','type':'invalid_request_error',
                              'param':'response_format','failed_generation':'sensitive-output'}})
    service._client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    ledger=Ledger(tmp_path/'one.json')
    try:
        bounded=make_bounded_service(ledger)
        await bounded.filter_and_recommend('Alternative to first product',[{'id':1,'name':'shoe','category':'shoes'},
                                                                         {'id':2,'name':'other shoe','category':'shoes'}])
        assert len(sent)==1 and ledger.state['calls_reserved']==1
        wire=sent[0]
        assert set(wire)=={'model','messages','temperature','max_tokens','top_p','response_format'}
        assert wire['model']=='openai/gpt-oss-120b' and wire['max_tokens']==256
        assert wire['temperature']==0.2 and wire['top_p']==0.9
        assert wire['response_format']=={'type':'json_object'}
        assert [m['role'] for m in wire['messages']]==['system','user']
        assert bounded.acceptance_error_metadata['provider_code']=='json_validate_failed'
        assert bounded.acceptance_error=='BadRequestError' and bounded.limits.retries==0
    finally:
        for name,value in saved.items():setattr(service,name,value)
        ledger.close()
