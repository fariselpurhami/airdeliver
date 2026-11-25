import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.shared_provider_admission import budgeted_turn,_turn_budget,SharedProviderBudgetError
from app.services.free_llm_service import FreeLLMService

@pytest.mark.asyncio
async def test_nested_real_turn_entry_reuses_one_budget_and_resets_after_failure():
    budgets=[]
    @budgeted_turn
    async def inner():
        budgets.append(_turn_budget.get());_turn_budget.get().take(1)
    @budgeted_turn
    async def outer():
        for _ in range(7):await inner()
    with pytest.raises(SharedProviderBudgetError):await outer()
    assert len({id(b) for b in budgets})==1 and _turn_budget.get() is None
    await inner()
    assert budgets[-1].calls==1

@pytest.mark.asyncio
async def test_request_dependency_closes_its_actual_client_after_exit(monkeypatch):
    import app.services.neural_core_service as module
    client=SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(module,'NeuralCoreService',lambda *args:SimpleNamespace(client=client))
    generator=module.get_neural_core_service(object(),object())
    assert (await anext(generator)).client is client
    await generator.aclose();client.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_singleton_client_shutdown_is_idempotent_and_lazy():
    svc=object.__new__(FreeLLMService);svc._client_lock=asyncio.Lock()
    client=SimpleNamespace(close=AsyncMock());svc._client=client
    await svc.aclose();await svc.aclose()
    assert svc._client is None;client.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_actual_nlu_entrypoints_install_budget_without_resetting_nested(monkeypatch):
    from app.services.ai_nlu_service import AINLUService
    svc=object.__new__(AINLUService)
    observed=[]
    def fail(payload):
        observed.append(_turn_budget.get());raise ValueError('controlled')
    svc._parse_incoming_message=fail
    with pytest.raises(ValueError):await svc.process_message({})
    assert observed[0] is not None and _turn_budget.get() is None
