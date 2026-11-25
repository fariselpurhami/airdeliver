"""Opt-in runner mechanics, no broker/provider connections."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from app.services.payment_outbox_reconciler import reconcile_once,run_reconciler
class Session:
 def __init__(self):self.rollback=AsyncMock()
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
@pytest.mark.asyncio
async def test_one_pass_rollback_and_cancel_are_not_suppressed(monkeypatch):
 db=Session();dispatch=AsyncMock(side_effect=RuntimeError('private event sentinel'))
 monkeypatch.setattr('app.services.payment_outbox_reconciler.dispatch_pending',dispatch)
 with pytest.raises(RuntimeError):await reconcile_once(lambda:db,object())
 db.rollback.assert_awaited_once()
 dispatch.side_effect=asyncio.CancelledError()
 with pytest.raises(asyncio.CancelledError):await reconcile_once(lambda:db,object())
 assert db.rollback.await_count==2
@pytest.mark.asyncio
async def test_recurring_runner_retains_failure_and_stops_cleanly(monkeypatch,caplog):
 stop=asyncio.Event();calls=[]
 async def once(*a,**kw):calls.append(kw);stop.set();raise RuntimeError('private event sentinel')
 monkeypatch.setattr('app.services.payment_outbox_reconciler.reconcile_once',once)
 await run_reconciler(lambda:Session(),object(),stop)
 assert len(calls)==1 and 'RuntimeError' in caplog.text and 'private event' not in caplog.text
@pytest.mark.asyncio
async def test_already_stopped_never_dispatches(monkeypatch):
 stop=asyncio.Event();stop.set();once=AsyncMock();monkeypatch.setattr('app.services.payment_outbox_reconciler.reconcile_once',once)
 await run_reconciler(lambda:Session(),object(),stop);once.assert_not_awaited()
@pytest.mark.asyncio
@pytest.mark.parametrize('kwargs',[{'batch_size':0},{'batch_size':True},{'deadline':0},{'interval':1}])
async def test_bad_bounds_fail_before_any_delivery(kwargs):
 with pytest.raises(ValueError):await run_reconciler(lambda:Session(),object(),asyncio.Event(),**kwargs)
