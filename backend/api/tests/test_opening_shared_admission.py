import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from tests.test_cart_persistence_outcomes import real_cache
from app.services.opening_admission import opening_generation
from app.services.shared_provider_admission import shared_provider_slot,SharedProviderBudgetError
from app.services.neural_core_service import _router_failure_notice,_safe_inference_failure

@pytest.mark.asyncio
async def test_actual_redis_active_only_lock_and_immediate_retry(real_cache):
    cache,_=real_cache
    async with opening_generation(cache,44,1) as first:
        assert first
        async with opening_generation(cache,44,1) as second:assert not second
        async with opening_generation(cache,45,1) as other:assert other
    async with opening_generation(cache,44,1) as retry:assert retry

@pytest.mark.asyncio
async def test_actual_entrypoint_duplicate_cannot_invoke_model_chain(real_cache):
    from app.services.ai_nlu_service import AINLUService
    cache,_=real_cache
    async def blocked(*args):await asyncio.sleep(.03);return True
    calls=AsyncMock(side_effect=blocked)
    services=[]
    for _ in range(2):
        svc=object.__new__(AINLUService);svc.cache=cache;svc.config=SimpleNamespace(matrix_timeout_sec=1)
        svc._handle_initial_suggestions_bounded=calls;svc._send_to_ui=AsyncMock();services.append(svc)
    await asyncio.gather(*(s._handle_initial_suggestions(99) for s in services))
    assert calls.await_count==1
    assert sum(s._send_to_ui.await_count for s in services)==0

def test_local_capacity_has_honest_separate_notice():
    exc=SharedProviderBudgetError('rolling_budget_or_cooldown_exhausted')
    assert _safe_inference_failure(exc)['failure_category']=='capacity'
    assert 'shared model capacity' in _router_failure_notice(exc)
    assert 'validate' not in _router_failure_notice(exc)

@pytest.mark.parametrize('text,category',[
    ('These are not popular products.','popularity'),
    ('No discount is claimed.','promotion'),
    ('There is no limited offer.','urgency'),
    ('This is not real stock.','real_stock'),
    ('Explore these synthetic test designs.','none'),
])
def test_fixture_rejection_categories_keep_negation_fail_closed(text,category):
    from app.services.shopping_copy import fixture_violation
    assert (fixture_violation(text) or 'none')==category

@pytest.mark.asyncio
async def test_active_lock_released_on_cancel_without_deleting_other_owner(real_cache):
    cache,_=real_cache;entered=asyncio.Event()
    async def block():
        async with opening_generation(cache,70,1):
            entered.set();await asyncio.Event().wait()
    task=asyncio.create_task(block());await entered.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    async with opening_generation(cache,70,1) as retry:assert retry
    async with opening_generation(cache,71,1):
        await cache.client.set('airdeliver:opening:active:v1:71','different-owner')
    assert await cache.client.get('airdeliver:opening:active:v1:71')=='different-owner'

@pytest.mark.asyncio
async def test_configured_lock_failure_never_runs_opening(real_cache):
    from app.services.ai_nlu_service import AINLUService
    cache,process=real_cache
    process.terminate();await asyncio.to_thread(process.wait,3)
    svc=object.__new__(AINLUService);svc.cache=cache;svc.config=SimpleNamespace(matrix_timeout_sec=1)
    svc._handle_initial_suggestions_bounded=AsyncMock();svc.ui=SimpleNamespace(publish=AsyncMock())
    await svc._handle_initial_suggestions(90)
    svc._handle_initial_suggestions_bounded.assert_not_awaited()
    assert svc.ui.publish.await_count==1
