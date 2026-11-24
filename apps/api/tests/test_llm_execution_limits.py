"""Regression tests for provider admission, response budgets and formatting.

No external providers are contacted. Instances bypass the production singleton
so older tests that replace singleton methods cannot hide these regressions.
"""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.free_llm_service import FreeLLMService


def service():
    instance = object.__new__(FreeLLMService)
    instance.__init__()
    return instance


def completion(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


@pytest.mark.asyncio
async def test_generate_response_keeps_paragraphs_and_requested_token_budget():
    svc = service()
    svc._chat_completion = AsyncMock(return_value=completion("  Answer\n\n- Fact one\n- Fact two  "))
    text = await svc.generate_response("A product question", max_tokens=120)
    assert text == "Answer\n\n- Fact one\n- Fact two"
    assert svc._chat_completion.await_args.kwargs["max_tokens"] == 120


@pytest.mark.asyncio
async def test_chat_completion_limits_concurrent_provider_calls():
    svc = service()
    svc.limits = replace(svc.limits, semaphore_limit=2, retries=0)
    svc._execution_semaphore = asyncio.Semaphore(2)
    active = peak = 0

    async def create(**kwargs):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        try:
            await asyncio.sleep(0.01)
            return completion("ok")
        finally:
            active -= 1

    svc._get_client = AsyncMock(return_value=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    await asyncio.gather(*[
        svc._chat_completion(messages=[{"role": "user", "content": "q"}], model="test-model")
        for _ in range(8)
    ])
    assert peak == 2


@pytest.mark.asyncio
async def test_chat_cancellation_releases_admission_slot():
    svc = service()
    svc._execution_semaphore = asyncio.Semaphore(1)
    entered = asyncio.Event()

    async def create(**kwargs):
        entered.set()
        await asyncio.sleep(30)

    svc._get_client = AsyncMock(return_value=SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    task = asyncio.create_task(svc._chat_completion(
        messages=[{"role": "user", "content": "q"}], model="test-model"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not svc._execution_semaphore.locked()


def provider(create):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.mark.asyncio
async def test_transient_provider_failure_retries_then_succeeds():
    import httpx
    from groq import APIConnectionError
    svc = service()
    create = AsyncMock(side_effect=[APIConnectionError(request=httpx.Request("POST", "https://provider.invalid")), completion("ok")])
    svc._get_client = AsyncMock(return_value=provider(create))
    assert (await svc._chat_completion(messages=[{"role": "user", "content": "q"}], model="test")).choices[0].message.content == "ok"
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_retry_backoff_is_inside_one_total_deadline():
    import httpx
    from groq import APIConnectionError
    svc = service()
    create = AsyncMock(side_effect=APIConnectionError(request=httpx.Request("POST", "https://provider.invalid")))
    svc._get_client = AsyncMock(return_value=provider(create))
    start = asyncio.get_running_loop().time()
    with pytest.raises(asyncio.TimeoutError):
        await svc._chat_completion(messages=[{"role": "user", "content": "q"}], model="test", timeout_seconds=.02)
    assert asyncio.get_running_loop().time() - start < .2
    assert create.await_count == 1


@pytest.mark.asyncio
async def test_invalid_provider_request_is_not_retried():
    import httpx
    from groq import BadRequestError
    svc = service()
    response = httpx.Response(400, request=httpx.Request("POST", "https://provider.invalid"))
    create = AsyncMock(side_effect=BadRequestError("bad request", response=response, body={}))
    svc._get_client = AsyncMock(return_value=provider(create))
    with pytest.raises(BadRequestError):
        await svc._chat_completion(messages=[{"role": "user", "content": "q"}], model="test")
    assert create.await_count == 1

@pytest.mark.asyncio
@pytest.mark.parametrize('header,value,expected',[('retry-after','0.01',True),('retry-after','600',False),('retry-after-ms','10',True)])
async def test_provider429_honors_retry_after_within_existing_deadline(header,value,expected):
    import httpx
    from groq import RateLimitError
    svc=service();response=httpx.Response(429,headers={header:value},request=httpx.Request('POST','https://provider.invalid'))
    create=AsyncMock(side_effect=[RateLimitError('quota',response=response,body={}),completion('ok')])
    svc._get_client=AsyncMock(return_value=provider(create))
    started=asyncio.get_running_loop().time()
    if expected:
        await svc._chat_completion(messages=[{'role':'user','content':'q'}],model='test',timeout_seconds=.5)
        assert create.await_count==2 and asyncio.get_running_loop().time()-started>=.009
    else:
        with pytest.raises(RateLimitError):await svc._chat_completion(messages=[{'role':'user','content':'q'}],model='test',timeout_seconds=.5)
        assert create.await_count==1


def test_retry_after_http_date_and_invalid_values():
    from app.services.free_llm_service import _provider_retry_delay
    from datetime import datetime,timedelta,timezone
    from email.utils import format_datetime
    exc=SimpleNamespace(response=SimpleNamespace(headers={'retry-after':format_datetime(datetime.now(timezone.utc)+timedelta(seconds=10))}))
    assert 8<=_provider_retry_delay(exc,0)<=10
    for value in ['nan','-1','nonsense']:
        exc.response.headers={'retry-after':value}
        assert _provider_retry_delay(exc,0)==.35
