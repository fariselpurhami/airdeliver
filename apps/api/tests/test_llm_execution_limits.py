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
