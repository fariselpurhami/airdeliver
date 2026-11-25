"""Actual confirm handler records checkout intent, never completed purchase."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.orchestration.worker_entrypoint import WorkerRuntime

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[False,True])
async def test_actual_checkout_handler_cannot_publish_buy_signal_before_payment(monkeypatch,failure):
    calls=[];tasks=[]
    class Session:
        async def __aenter__(self):return object()
        async def __aexit__(self,*args):return False
    class Checkout:
        def __init__(self,*args):pass
        async def handle_confirm_order(self,payload):
            if failure:raise RuntimeError('checkout failed')
            calls.append(payload)
    monkeypatch.setattr('app.services.ai_checkout_service.AICheckoutService',Checkout)
    rt=object.__new__(WorkerRuntime)
    rt.services=SimpleNamespace(session_maker=Session,cache=object(),rabbitmq=object(),payment=object(),behavior=object())
    rt.wait_for_readiness=AsyncMock();rt.track_behavior=AsyncMock()
    def spawn(coro,name):tasks.append(asyncio.create_task(coro))
    rt.create_background_task=spawn
    payload={'user_id':7,'order_id':3}
    if failure:
        with pytest.raises(RuntimeError):await rt.confirm_order_handler_impl(payload)
    else:await rt.confirm_order_handler_impl(payload)
    await asyncio.gather(*tasks)
    rt.track_behavior.assert_awaited_once_with(7,'checkout',{'context':'checkout_initiated'})
    assert calls==([] if failure else [payload])
