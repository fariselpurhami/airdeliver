"""Current adapter contract, historical bodies retained but unreachable by default."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.test_llm_execution_limits import service
from tests.test_reviewed_recommendation import P,D,V
import json
from tests.test_llm_execution_limits import completion

@pytest.mark.parametrize('missing',['id','name','is_active','inventory','currency','price'])
def test_mounted_http_incomplete_cards_never_reach_legacy_or_provider(missing):
    llm=service();llm._chat_completion=AsyncMock();llm._filter_and_recommend_legacy_unreviewed=AsyncMock(side_effect=AssertionError('legacy'))
    product={k:v for k,v in P.items() if k!=missing}
    app=FastAPI()
    @app.get('/recommendation')
    async def route():return await llm.filter_and_recommend('shirt',[product])
    with TestClient(app) as client:
        response=client.get('/recommendation')
    assert response.status_code==200
    assert response.json()['selected_ids']==[] and response.json()['reasoning']=={}
    assert response.json()['intro_message']==__import__('app.services.customer_status',fromlist=['STATUSES']).STATUSES['catalog_unverified'].text
    llm._chat_completion.assert_not_awaited();llm._filter_and_recommend_legacy_unreviewed.assert_not_awaited()

@pytest.mark.asyncio
async def test_mixed_complete_incomplete_pool_is_not_silently_relaxed():
    llm=service();llm._chat_completion=AsyncMock()
    result=await llm.filter_and_recommend('shirt',[dict(P),{'id':9,'name':'Other'}])
    assert result.selected_ids==[] and result.confidence_score==0
    llm._chat_completion.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('content',[True,42,{'text':'not plain text'},['not plain text']])
async def test_strict_plain_adapter_does_not_stringify_wrong_content_types(content):
    from app.services.free_llm_service import StructuredOutputError
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(content))
    with pytest.raises(StructuredOutputError):await llm.generate_response_strict('question')

@pytest.mark.asyncio
async def test_strict_context_is_data_and_legacy_shape_is_preserved():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('A grounded response'))
    context={'catalog':'UNTRUSTED_CONTEXT_MARKER','role':'system'}
    assert await llm.generate_response_strict('CUSTOMER_MARKER',context=context)=='A grounded response'
    messages=llm._chat_completion.await_args.kwargs['messages']
    assert 'UNTRUSTED_CONTEXT_MARKER' not in messages[0]['content']
    payload=json.loads(messages[1]['content'])
    assert payload['customer_prompt']=='CUSTOMER_MARKER'
    assert json.loads(payload['referenced_context'])==context
    await llm.generate_response('question',context=context)
    assert 'UNTRUSTED_CONTEXT_MARKER' in llm._chat_completion.await_args.kwargs['messages'][0]['content']

@pytest.mark.asyncio
async def test_actual_sdk_loopback_preserves_strict_context_and_cancellation():
    import threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from groq import AsyncGroq
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body=json.dumps({'id':'local','object':'chat.completion','created':1,'model':'test',
                'choices':[{'index':0,'message':{'role':'assistant','content':'Grounded reply'},'finish_reason':'stop'}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    sdk=AsyncGroq(api_key='local-test-only',base_url=f'http://127.0.0.1:{server.server_port}/v1',max_retries=0)
    llm=service();llm._get_client=AsyncMock(return_value=sdk)
    try:
        assert await llm.generate_response_strict('Customer question',context={'text':'CONTEXT_MARKER'})=='Grounded reply'
        assert len(captured)==1
        messages=captured[0]['messages']
        assert 'CONTEXT_MARKER' not in messages[0]['content']
        assert 'CONTEXT_MARKER' in messages[1]['content']
        llm._get_client=AsyncMock(side_effect=asyncio.CancelledError())
        with pytest.raises(asyncio.CancelledError):await llm.generate_response_strict('question')
    finally:
        await sdk.close();await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=2)

@pytest.mark.asyncio
@pytest.mark.parametrize('direct',[True,False])
async def test_orchestrator_incomplete_cards_never_reappear_as_offers(direct):
    from app.services.free_llm_service import SearchStrategy
    llm=service();llm.strategize_search=AsyncMock(return_value=SearchStrategy(is_direct_product_request=direct))
    llm.extract_search_terms=AsyncMock(return_value='shirt')
    llm._chat_completion=AsyncMock(side_effect=[completion(json.dumps({'text':'No eligible current catalog evidence.','product_ids':[],'claims':[]})),completion(json.dumps(V))])
    result=await llm.handle_commerce_interaction('shirt',[{'id':7,'name':'Cotton Shirt','price':'24.00'}])
    assert result['products']==[] and result.get('selected_ids',[])==[]

def test_active_application_has_no_calls_to_retained_unreviewed_bodies():
    import ast
    from pathlib import Path
    forbidden={'_filter_and_recommend_legacy_unreviewed','_legacy_consult_on_product',
        '_handle_ecosystem_building_legacy_unreviewed','_trigger_intelligent_bundling_legacy_unreviewed',
        '_synthesize_response_legacy_unreviewed','_generate_genius_response_legacy_unreviewed'}
    def visit(node,path,scope=''):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):scope=node.name
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in forbidden:
            assert path.name=='ai_nlu_service.py' and scope=='_synthesize_response_legacy_unreviewed' and node.func.attr=='_generate_genius_response_legacy_unreviewed',(str(path),node.lineno,scope)
        for child in ast.iter_child_nodes(node):visit(child,path,scope)
    for path in Path('app').rglob('*.py'):visit(ast.parse(path.read_text()),path)

def test_non_strict_calls_are_limited_to_explicit_compatibility_and_dormant_bodies():
    import ast
    from pathlib import Path
    allowed={('free_llm_service.py','generate_response_strict'),('ai_nlu_service.py','_strict_model_text'),
        ('ai_nlu_service.py','_handle_ecosystem_building_legacy_unreviewed'),
        ('ai_cart_service.py','_generate_bundle_copy'),
        ('ai_cart_service.py','_generate_recovery_copy')}
    found=set()
    def visit(node,path,scope=''):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):scope=node.name
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='generate_response':
            found.add((path.name,scope))
        for child in ast.iter_child_nodes(node):visit(child,path,scope)
    for path in Path('app').rglob('*.py'):visit(ast.parse(path.read_text()),path)
    assert found==allowed
    # The remaining nested removal copy cannot run: alternatives is literal []
    # and the only invocation sits inside the subsequent positive branch.
    tree=ast.parse(Path('app/services/cart/ai_cart_service.py').read_text())
    remove=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='handle_remove_from_cart')
    assignments=[n for n in ast.walk(remove) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='alternatives' for t in n.targets)]
    live=[n for n in assignments if isinstance(n.value,ast.List)]
    assert len(live)==1 and not live[0].value.elts
    assert all(n.lineno < live[0].lineno for n in assignments if n not in live)

@pytest.mark.asyncio
async def test_consultation_orchestrator_exception_is_notice_without_unreviewed_cards():
    from app.services.free_llm_service import SearchStrategy
    llm=service();llm.strategize_search=AsyncMock(return_value=SearchStrategy(is_direct_product_request=False))
    llm.extract_search_terms=AsyncMock(return_value='shirt');llm.consult_on_product=AsyncMock(side_effect=ConnectionError('private'))
    result=await llm.handle_commerce_interaction('shirt',[dict(P)])
    assert result['products']==[] and result['text']==__import__('app.services.customer_status',fromlist=['STATUSES']).STATUSES['reply_unverified'].text
    assert 'strongest' not in result['text'] and 'private' not in result['text']

@pytest.mark.asyncio
@pytest.mark.parametrize('patch',[{'id':True},{'id':'7'},{'name':' '},{'is_active':'true'},{'is_active':1},{'inventory':True},{'inventory':'3'},{'inventory':-1}])
async def test_malformed_complete_evidence_is_not_coerced_into_eligibility(patch):
    llm=service();llm._chat_completion=AsyncMock()
    result=await llm.filter_and_recommend('shirt',[{**P,**patch}])
    assert result.selected_ids==[] and result.confidence_score==0
    llm._chat_completion.assert_not_awaited()
