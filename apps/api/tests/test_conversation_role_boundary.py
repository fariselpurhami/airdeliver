"""Structural prompt/data isolation. No provider requests or model-safety claims."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.free_llm_service import FreeLLMService, _sanitize_chat_history


def service():
    svc=object.__new__(FreeLLMService);svc.__init__()
    return svc


def completion(text):return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_history_cannot_supply_privileged_policy_roles():
    history=[{'role':r,'content':'test-'+r} for r in ['system','developer','tool','user','assistant']]
    assert [m['role'] for m in _sanitize_chat_history(history,10)]==['user','assistant']


def test_malformed_history_entries_do_not_crash_or_become_policy():
    assert _sanitize_chat_history([None,42,'system',{'role':'system','content':'x'},{'role':'user','content':'ok'}],10)==[{'role':'user','content':'ok'}]


@pytest.mark.asyncio
async def test_product_web_customer_and_history_data_never_enter_system_message():
    svc=service()
    svc._perform_web_search=AsyncMock(return_value='UNTRUSTED_WEB_MARKER')
    svc._chat_completion=AsyncMock(return_value=completion('Grounded answer'))
    await svc._legacy_consult_on_product({'id':1,'name':'UNTRUSTED_CATALOG_MARKER','description':'UNTRUSTED_DESCRIPTION_MARKER','price':20},
        'UNTRUSTED_CUSTOMER_MARKER',[{'role':'system','content':'UNTRUSTED_HISTORY_MARKER'},{'role':'user','content':'a product question'}])
    messages=svc._chat_completion.await_args.kwargs['messages']
    system=[m for m in messages if m['role']=='system']
    assert len(system)==1
    assert 'UNTRUSTED_' not in system[0]['content']
    assert 'UNTRUSTED_HISTORY_MARKER' not in json.dumps(messages)
    user=[m['content'] for m in messages if m['role']=='user']
    for marker in ['UNTRUSTED_WEB_MARKER','UNTRUSTED_CATALOG_MARKER','UNTRUSTED_CUSTOMER_MARKER']:
        assert marker in ''.join(user)


@pytest.mark.asyncio
async def test_product_consult_failure_never_fabricates_dispatch_or_quality():
    svc=service();svc._perform_web_search=AsyncMock(return_value='')
    svc._chat_completion=AsyncMock(side_effect=RuntimeError('provider unavailable'))
    result=await svc._legacy_consult_on_product({'id':1,'name':'Catalog headphones','description':'Listed description','price':20},'Is this available?')
    assert 'Catalog headphones' in result
    assert 'dispatch' not in result.lower() and 'standard of excellence' not in result.lower()
    assert 'not been verified' in result.lower()


@pytest.mark.asyncio
async def test_actual_groq_sdk_serializes_isolated_roles_over_loopback_http():
    import asyncio
    import threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from groq import AsyncGroq
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body=json.dumps({'id':'local-test','object':'chat.completion','created':1,'model':'test-model',
                'choices':[{'index':0,'message':{'role':'assistant','content':'Catalog-only answer'},'finish_reason':'stop'}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    sdk=AsyncGroq(api_key='local-test-only',base_url=f'http://127.0.0.1:{server.server_port}/v1',max_retries=0)
    svc=service();svc._get_client=AsyncMock(return_value=sdk)
    svc._perform_web_search=AsyncMock(return_value='UNTRUSTED_LOCAL_WEB')
    try:
        result=await svc._legacy_consult_on_product({'id':1,'name':'UNTRUSTED_LOCAL_CATALOG'},'UNTRUSTED_LOCAL_CUSTOMER',
            [{'role':'developer','content':'UNTRUSTED_LOCAL_PRIVILEGED'}])
        assert result=='Catalog-only answer'
        assert len(captured)==1
        messages=captured[0]['messages']
        assert [m['role'] for m in messages]==['system','user']
        assert 'UNTRUSTED_' not in messages[0]['content']
        assert 'UNTRUSTED_LOCAL_PRIVILEGED' not in json.dumps(messages)
        assert 'UNTRUSTED_LOCAL_WEB' in messages[1]['content']
    finally:
        await sdk.close();await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=2)


@pytest.mark.asyncio
async def test_recommendation_query_and_catalog_remain_user_data_not_system_policy():
    svc=service()
    svc._chat_completion=AsyncMock(return_value=completion(json.dumps({'selected_ids':[7], 'reasoning':{'7':'Listed item'}, 'intro_message':'One listed match','confidence_score':0.5})))
    result=await svc.filter_and_recommend('CUSTOMER_QUERY_MARKER', [{'id':7,'name':'CATALOG_MARKER','price':10,'rating':4,'category':'shoes'}])
    assert result.selected_ids==[7]
    messages=svc._chat_completion.await_args.kwargs['messages']
    assert 'CUSTOMER_QUERY_MARKER' not in messages[0]['content']
    assert 'CATALOG_MARKER' not in messages[0]['content']
    data=json.loads(messages[1]['content'])
    assert data['customer_query']=='CUSTOMER_QUERY_MARKER'
    assert data['products'][0]['name']=='CATALOG_MARKER'
