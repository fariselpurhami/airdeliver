import json, logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest, httpx
from groq import BadRequestError
from app.services.provider_json_diagnostics import failed_json_diagnostics
from app.services.opening_batch_copy import opening_schema
from app.services.structured_output import response_format
from tests.test_cart_persistence_outcomes import real_cache
from app.services.shared_provider_admission import shared_provider_slot, SharedProviderBudgetError

@pytest.mark.parametrize('raw,expected', [('{"private-secret":', 'invalid'), (json.dumps({'Personalized': {'introduction': 'private-secret', 'insight': 'private-insight', 'product_ids': [], 'claims': []}}), 'no_detected_violation'), (json.dumps({'private-secret': {}}), 'violation'), (json.dumps({'Personalized': {'introduction': 8, 'insight': 'private', 'product_ids': [], 'claims': []}}), 'violation')])
def test_structural_categories_without_values(raw, expected):
    wire = response_format('openai/gpt-oss-120b', opening_schema(['Personalized']))
    value = failed_json_diagnostics(SimpleNamespace(body={'error': {'failed_generation': raw}}), wire, 1800)
    assert value.get('schema', value['json']) == expected
    assert 'private' not in json.dumps(value)

def test_cap_only_when_explicit_numeric_usage_or_finish_evidence():
    base = {'failed_generation': '{}', 'finish_reason': []}
    assert 'output_cap_reached' not in failed_json_diagnostics(SimpleNamespace(body=base), {}, 1800)
    base.update(usage={'completion_tokens': 1800}, finish_reason='length')
    value = failed_json_diagnostics(SimpleNamespace(body=base), {}, 1800)
    assert value['output_cap_reached'] is True and value['finish'] == 'length'

@pytest.mark.asyncio
async def test_denied_admission_does_not_mutate_shared_ledger(real_cache):
    (cache, _) = real_cache
    async with shared_provider_slot('offline-denied-ledger', [], {}, 100, client=cache.client, limit=1000) as reservation:
        reservation.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=950)))
    keys = await cache.client.keys('airdeliver:provider:*:usage')
    assert len(keys) == 1
    before = await cache.client.zrange(keys[0], 0, -1, withscores=True)
    for _ in range(3):
        with pytest.raises(SharedProviderBudgetError):
            async with shared_provider_slot('offline-denied-ledger', [], {}, 100, client=cache.client, limit=1000):
                pytest.fail('denied')
    assert await cache.client.zrange(keys[0], 0, -1, withscores=True) == before

@pytest.mark.asyncio
async def test_native_adapter_logs_categories_never_failed_generation(caplog):
    from app.services.free_llm_service import FreeLLMService
    svc = object.__new__(FreeLLMService)
    svc.__init__()
    response = httpx.Response(400, request=httpx.Request('POST', 'http://localhost/offline'))
    error = BadRequestError('private-provider-body', response=response, body={'code': 'json_validate_failed', 'failed_generation': '{"private-secret":'})
    svc._get_client = AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=error)))))
    with caplog.at_level(logging.WARNING), pytest.raises(BadRequestError):
        await svc._chat_completion(model='offline-json', messages=[{'role': 'user', 'content': 'private-customer'}], response_format={}, timeout_seconds=1, max_tokens=1800)
    assert 'llm_provider_json_diagnostics' in caplog.text and "'json': 'invalid'" in caplog.text
    assert 'private-' not in caplog.text

@pytest.mark.parametrize('raw', ['[' * 2000, 'NaN', 'x' * 100001], ids=['deep', 'constant', 'oversize'])
def test_untrusted_generation_is_bounded_and_never_masks_provider_failure(raw):
    result = failed_json_diagnostics(SimpleNamespace(body={'failed_generation': raw}), {}, 1800)
    assert result['json'] in {'invalid', 'invalid_or_complex', 'oversize'}

def test_missing_generation_and_duplicates_and_length_categories():
    assert failed_json_diagnostics(SimpleNamespace(body={}), {}, 1800) == {'generation': 'absent'}
    wire = {'json_schema': {'schema': {'type': 'object', 'properties': {'x': {'type': 'string', 'maxLength': 2}}, 'additionalProperties': False}}}
    result = failed_json_diagnostics(SimpleNamespace(body={'failed_generation': '{"x":"private","x":"secret"}'}), wire, 1800)
    assert result['duplicate_keys'] is True and result['categories'] == ['text_too_long']
    assert 'secret' not in str(result)
