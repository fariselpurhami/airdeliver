"""Offline tests for the optional OpenRouter free-model client. httpx MockTransport only: no network, no key, no provider call."""
import asyncio
import json

import httpx
import pytest
from groq import APIStatusError, RateLimitError

from app.services.conversation.openrouter_adapter import (DEFAULT_FREE_MODEL, DailyCapReached, OpenRouterClient,
                                                           OpenRouterConfigError)

OK = {'id': 'x', 'object': 'chat.completion', 'created': 1, 'model': DEFAULT_FREE_MODEL,
      'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '{"opening":"a","question":"b"}', 'reasoning': 'hidden'}}],
      'usage': {'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3}}


def client(handler, **kw):
    return OpenRouterClient(api_key='test-key', http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **kw)


def run(coro):
    return asyncio.run(coro)


def test_free_only_payload_floor_and_key_in_header_only():
    seen = {}

    def handler(req):
        seen['auth'] = req.headers['authorization']
        seen['url'] = str(req.url)
        seen['body'] = json.loads(req.content)
        return httpx.Response(200, json=OK)

    c = client(handler)
    r = run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=[{'role': 'user', 'content': 'hi'}], max_tokens=256,
                                      temperature=0.2, response_format={'type': 'json_schema', 'json_schema': {}}, reasoning_effort='low'))
    assert r.choices[0].message.content.startswith('{"opening"')
    assert seen['url'] == 'https://openrouter.ai/api/v1/chat/completions' and seen['auth'] == 'Bearer test-key'
    b = seen['body']
    assert b['max_tokens'] == 1024  # reasoning model: the writer/reviewer budget (256) would truncate
    assert b['response_format'] == {'type': 'json_object'} and b['reasoning'] == {'effort': 'low', 'exclude': True}
    assert 'reasoning_effort' not in b and 'test-key' not in json.dumps(b)
    assert c.used_today == 1


def test_paid_models_are_refused_before_any_request():
    called = []
    c = client(lambda req: called.append(1) or httpx.Response(200, json=OK))
    for model in ('nvidia/nemotron-3-ultra-550b-a55b', 'openai/gpt-oss-120b', None):
        with pytest.raises(OpenRouterConfigError):
            run(c.chat.completions.create(model=model, messages=[{'role': 'user', 'content': 'hi'}]))
    assert not called and c.used_today == 0


def test_local_cap_fails_closed_and_429_is_raised_once_without_retry():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429, json={'error': {'message': 'limit'}})

    c = client(handler, daily_cap=2)
    msg = [{'role': 'user', 'content': 'hi'}]
    with pytest.raises(RateLimitError):
        run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
    with pytest.raises(RateLimitError):
        run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
    with pytest.raises(DailyCapReached):
        run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
    assert len(calls) == 2  # never retried, third call never sent


def test_server_error_and_config_bounds():
    c = client(lambda req: httpx.Response(503, json={}))
    with pytest.raises(APIStatusError):
        run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=[{'role': 'user', 'content': 'hi'}]))
    for bad in ({'api_key': ' '}, {'api_key': 'k', 'daily_cap': 51}, {'api_key': 'k', 'daily_cap': 0}, {'api_key': 'k', 'base_url': 'http://x'}, {'api_key': 'k', 'json_mode': 'x'}):
        with pytest.raises(OpenRouterConfigError):
            OpenRouterClient(**bad)


def test_daily_counter_rolls_over_with_the_clock():
    now = [86400 * 10]
    c = client(lambda req: httpx.Response(200, json=OK), daily_cap=1, clock=lambda: now[0])
    msg = [{'role': 'user', 'content': 'hi'}]
    run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
    with pytest.raises(DailyCapReached):
        run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
    now[0] += 86400
    run(c.chat.completions.create(model=DEFAULT_FREE_MODEL, messages=msg))
