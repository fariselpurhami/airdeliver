import asyncio
from types import SimpleNamespace
import pytest
from scripts.accept_dev_cart import Ledger, AcceptanceStopped, make_bounded_service


def test_persistent_ledger_rejects_rerun_and_reserves_failures(tmp_path):
    path = tmp_path / 'approval.json'
    ledger = Ledger(path)
    for _ in range(8): ledger.reserve_call()
    with pytest.raises(AcceptanceStopped): ledger.reserve_call()
    assert ledger.state['calls_reserved'] == 8
    ledger.close()
    with pytest.raises(FileExistsError): Ledger(path)
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_real_service_wrapper_caps_tokens_retries_and_model(tmp_path, monkeypatch):
    from app.services.free_llm_service import FreeLLMService
    service = FreeLLMService()
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[])
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    ledger = Ledger(tmp_path / 'cap.json')
    # Restore singleton modifications so other production-service tests stay independent.
    old_chat, old_limits = service._chat_completion, service.limits
    monkeypatch.setattr(service, '_chat_completion', old_chat)
    monkeypatch.setattr(service, 'limits', old_limits)
    try:
        bounded = make_bounded_service(ledger)
        assert bounded.limits.retries == 0
        await bounded._chat_completion(messages=[{'role':'user','content':'test'}], model='openai/gpt-oss-120b', max_tokens=1000)
        assert calls[0]['max_tokens'] == 256
        with pytest.raises(AcceptanceStopped):
            await bounded._chat_completion(messages=[], model='other')
        assert ledger.state['calls_reserved'] == 1
    finally:
        service._chat_completion = old_chat; service.limits = old_limits; service._client = None
        ledger.close()


@pytest.mark.asyncio
async def test_provider_failure_is_not_retried_and_stops_after_reservation(tmp_path, monkeypatch):
    from app.services.free_llm_service import FreeLLMService
    from groq import RateLimitError
    import httpx
    service = FreeLLMService()
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        raise RateLimitError('quota', response=httpx.Response(429, request=httpx.Request('POST','https://api.groq.com')), body={})
    old_chat, old_limits, old_client = service._chat_completion, service.limits, service._client
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    ledger = Ledger(tmp_path / 'error.json')
    try:
        bounded = make_bounded_service(ledger)
        with pytest.raises(RateLimitError):
            await bounded._chat_completion(messages=[{'role':'user','content':'test'}], model='openai/gpt-oss-120b')
        assert len(calls) == 1 and ledger.state['calls_reserved'] == 1
        assert bounded.acceptance_error == 'RateLimitError'
    finally:
        service._chat_completion = old_chat; service.limits = old_limits; service._client = old_client
        ledger.close()
