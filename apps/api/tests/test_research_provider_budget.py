"""Offline transport, quota privacy, deadline and evidence-budget regressions."""
import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from groq import AsyncGroq, RateLimitError
from app.services.provider_budget import (complete, admission, quota_metadata,
    ProviderCooldownError, ProviderInputBudgetError, token_upper_bound)
from app.services.research_evidence_budget import pack_sources


def rate_error(delay='120'):
    response = httpx.Response(429, headers={'retry-after': delay,
        'x-ratelimit-remaining-tokens': '0', 'x-ratelimit-reset-tokens': '1m2s',
        'x-ratelimit-remaining-requests': 'private-secret'},
        request=httpx.Request('POST', 'http://127.0.0.1/offline'))
    return RateLimitError('secret-prompt', response=response,
        body={'error': {'message': 'secret-org tokens per day (TPD)'}})

@pytest.mark.asyncio
async def test_long_reset_no_early_retry_and_next_instance_admission_blocked(caplog):
    model = 'offline-long'
    create = AsyncMock(side_effect=rate_error())
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RateLimitError):
            await complete(create, model=model, messages=[{'role':'user','content':'secret-prompt'}], response_format={}, timeout=.05)
        with pytest.raises(ProviderCooldownError):
            await complete(create, model=model, messages=[], response_format={}, timeout=.01)
    assert create.await_count == 1
    assert 'TPD' in caplog.text and 'secret' not in caplog.text

@pytest.mark.asyncio
async def test_short_reset_retries_within_deadline():
    create=AsyncMock(side_effect=[rate_error('.01'), 'ok'])
    start=asyncio.get_running_loop().time()
    assert await complete(create,model='offline-short',messages=[],response_format={},timeout=.2)=='ok'
    assert asyncio.get_running_loop().time()-start >= .009
    assert create.await_count==2

@pytest.mark.asyncio
async def test_queue_timeout_and_cancellation_release_shared_slot():
    state=admission('offline-queue')
    async with state.lock:
        with pytest.raises(TimeoutError):
            await complete(AsyncMock(),model='offline-queue',messages=[],response_format={},timeout=.01)
    assert not state.lock.locked()
    entered=asyncio.Event()
    async def wait(**kwargs):
        entered.set()
        await asyncio.Event().wait()
    task=asyncio.create_task(complete(wait,model='offline-queue',messages=[],response_format={},timeout=30))
    await entered.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert not state.lock.locked()

@pytest.mark.asyncio
async def test_multilingual_oversize_never_sent():
    create=AsyncMock()
    with pytest.raises(ProviderInputBudgetError):
        await complete(create,model='offline-big',messages=[{'content':'مواصفات'*2000}],response_format={},timeout=.1,stage='SpecDraft')
    create.assert_not_called()


def test_safe_quota_headers_and_unicode_evidence_preserve_exact_substring():
    metadata=quota_metadata(rate_error())
    assert metadata=={'remaining_tokens':0,'retry_after':'120','reset_tokens':'1m2s','quota_unit':'TPD'}
    source={'url':'https://maker.example/specs','text':'noise '*1000+' Alpha مواصفات شاشة OLED '+ 'tail '*1000}
    packed=pack_sources([source], 'Alpha مواصفات OLED', byte_budget=150)
    assert packed[0]['text'] in source['text']
    assert len(packed[0]['text'].encode())<=150
    assert 'OLED' in packed[0]['text']
    assert token_upper_bound({'content':'م'}) > token_upper_bound({'content':'a'})

@pytest.mark.asyncio
async def test_native_sdk_http429_uses_one_request_and_output_cap():
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from threading import Thread
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            body=json.dumps({'error':{'message':'private-secret (TPM)','type':'rate_limit_error'}}).encode()
            self.send_response(429);self.send_header('Content-Type','application/json')
            self.send_header('Retry-After','90');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        async with AsyncGroq(api_key='offline-test',base_url=f'http://127.0.0.1:{server.server_port}',max_retries=0) as client:
            with pytest.raises(RateLimitError):
                await complete(client.chat.completions.create,model='offline-native',messages=[{'role':'user','content':'local test'}],response_format={'type':'json_object'},stage='SourceReview',timeout=.5)
        assert len(seen)==1 and seen[0]['max_tokens']==1200
    finally:
        server.shutdown();server.server_close();thread.join()

@pytest.mark.asyncio
async def test_actual_extraction_review_are_packed_and_keep_strict_schema():
    from app.services.neural_core_service import NeuralCoreService
    from app.services.product_knowledge_service import answer_product_question
    calls=[]
    async def create(**kwargs):
        calls.append(kwargs)
        name=kwargs['response_format']['json_schema']['name']
        if name=='SpecDraft':
            content={'facts':[{'label':'Display','statement':'OLED panel','quote':'Alpha OLED display.','source':0}],'covered_targets':['Alpha']}
        else:content={'supported':True,'exact_model':True,'product_information_only':True}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(content)))])
    service=object.__new__(NeuralCoreService)
    service.profile=SimpleNamespace(support_model='openai/gpt-oss-120b')
    service.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    async def lookup(q):
        return [{'url':f'https://maker.example/spec{i}','text':'irrelevant '*250+' Alpha OLED display. '+'tail '*250} for i in range(3)]
    result=await answer_product_question(service._execute_llm_inference,'Alpha OLED display specs',targets=('Alpha',),lookup=lookup)
    assert 'OLED panel' in result.text
    assert len(calls)==2
    for call in calls:
        assert call['response_format']['json_schema']['strict'] is True
        assert token_upper_bound({'messages':call['messages'],'response_format':call['response_format']})+call['max_tokens']<=7800
