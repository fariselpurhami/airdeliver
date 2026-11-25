"""No provider requests. Real httpx stream lifetime against controlled transport."""
import asyncio,json
import httpx
import pytest
from unittest.mock import AsyncMock
from app.services import tavily_boundary as boundary
from app.services import product_knowledge_service as knowledge
from tests.test_llm_execution_limits import service

@pytest.mark.asyncio
@pytest.mark.parametrize('payload',[None,[],42,{'results':None},{'results':{}},{'results':'bad'}])
async def test_malformed_top_level_never_becomes_source(monkeypatch,payload):
    real=httpx.AsyncClient
    monkeypatch.setattr(boundary.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=payload)),**kw))
    with pytest.raises(ValueError):await boundary.search('question','test-only-key')

@pytest.mark.parametrize('url',['http://maker.example/spec','https://127.0.0.1/spec','https://user:pass@maker.example/spec','https://maker.local/spec','https://maker.example:444/spec','file:///private','https://maker.example/spec'])
def test_source_policy_and_duplicate_shape(url):
    result={'answer':'unsupported answer','results':[None,{'url':url,'content':'Source evidence'},{'url':url,'content':'Duplicate'}]}
    rows=boundary.source_rows(result)
    assert rows==([{'url':url,'text':'Source evidence'}] if url=='https://maker.example/spec' else [])

@pytest.mark.asyncio
async def test_request_is_fixed_bounded_no_synthetic_answer_and_sources_preserved(monkeypatch):
    real=httpx.AsyncClient;seen=[]
    def handler(req):
        seen.append(req)
        return httpx.Response(200,json={'answer':'DO NOT USE SUMMARY','results':[{'url':'https://maker.example/spec','content':'An exact source excerpt'}]})
    monkeypatch.setattr(boundary.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(handler),**kw))
    llm=service();llm._tavily_api_key='test-only-key'
    result=await llm._perform_web_search('product question')
    assert 'An exact source excerpt' in result and 'https://maker.example/spec' in result
    assert 'DO NOT USE SUMMARY' not in result and 'Untrusted search excerpts' in result
    body=json.loads(seen[0].content)
    assert body['max_results']==3 and body['include_answer'] is False
    assert str(seen[0].url)=='https://api.tavily.com/search'

@pytest.mark.asyncio
@pytest.mark.parametrize('status',[401,403,429,500,400])
async def test_source_errors_keep_typed_notices_and_no_raw_payload(monkeypatch,status):
    real=httpx.AsyncClient
    monkeypatch.setenv('TAVILY_API_KEY','test-only-key')
    monkeypatch.setattr(boundary.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(status,text='PRIVATE_PAYLOAD')),**kw))
    with pytest.raises(knowledge.SourceFailure) as error:await knowledge.lookup_product_sources('product')
    assert error.value.cause==({401:'authentication',403:'authentication',429:'rate_limit',500:'provider_server',400:'provider_request'}[status])
    assert 'PRIVATE' not in str(error.value)

class Stream(httpx.AsyncByteStream):
    def __init__(self,mode):self.mode=mode;self.closed=False;self.entered=asyncio.Event()
    async def __aiter__(self):
        self.entered.set()
        if self.mode=='oversize':yield b'x'*(boundary.MAX_BYTES+1)
        else:await asyncio.Event().wait()
    async def aclose(self):self.closed=True

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['oversize','cancel','deadline'])
async def test_stream_is_closed_on_limits_cancellation_and_total_deadline(monkeypatch,mode):
    stream=Stream(mode);real=httpx.AsyncClient
    monkeypatch.setattr(boundary.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=stream)),**kw))
    if mode=='oversize':
        with pytest.raises(ValueError):await boundary.search('product','test-only-key')
    elif mode=='deadline':
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(.02):await boundary.search('product','test-only-key')
    else:
        task=asyncio.create_task(boundary.search('product','test-only-key'))
        await stream.entered.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    assert stream.closed

@pytest.mark.asyncio
@pytest.mark.parametrize('row',[None,{'url':'https://maker.example/x','title':42},{'url':'http://127.0.0.1/x','title':'unsafe'},{'url':'https://maker.example/x','title':'Actual maker title'}])
async def test_title_hint_uses_only_valid_source_strings(monkeypatch,row):
    monkeypatch.setattr(boundary,'search',AsyncMock(return_value={'results':[row]}))
    llm=service();llm._tavily_api_key='test-only-key'
    result=await llm._perform_tavily_title_lookup('product')
    assert result==('Actual maker title' if isinstance(row,dict) and row.get('title')=='Actual maker title' else '')

def test_sync_tavily_sdk_only_remains_inside_preserved_legacy_bodies():
    import ast
    from pathlib import Path
    found=[]
    def visit(node,scope=()):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):scope=(*scope,node.name)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='TavilyClient':found.append(scope[0])
        for child in ast.iter_child_nodes(node):visit(child,scope)
    visit(ast.parse(Path('app/services/conversation/free_llm_service.py').read_text()))
    assert set(found)=={'_perform_tavily_title_lookup_legacy_unreviewed','_perform_web_search_legacy_unreviewed'}
    for path in Path('app').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in {'_perform_tavily_title_lookup_legacy_unreviewed','_perform_web_search_legacy_unreviewed'}

@pytest.mark.asyncio
async def test_own_transport_deadline_closes_stream(monkeypatch):
    stream=Stream('deadline');real=httpx.AsyncClient
    monkeypatch.setattr(boundary.httpx,'AsyncClient',lambda **kw:real(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=stream)),**kw))
    with pytest.raises(TimeoutError):await boundary.search('product','test-only-key',timeout=.02)
    assert stream.closed
