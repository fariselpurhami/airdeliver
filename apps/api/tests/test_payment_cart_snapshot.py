"""Combined migrated PostgreSQL checkout and real Redis payment cleanup."""
import copy
from unittest.mock import AsyncMock

import pytest
from sqlmodel import select
from app.models.order import Order
from app.services.ai_checkout_service import AICheckoutService
from app.services.payment_completion_service import PaymentCompletionService
from app.services.rabbitmq_service import PublishOutcome, PublishResult
from tests.test_checkout_postgres import pg_checkout
from tests.test_cart_persistence_outcomes import real_cache


@pytest.mark.asyncio
@pytest.mark.parametrize('changed,legacy',[(False,False),(True,False),(True,True)])
async def test_payment_cleanup_only_removes_frozen_cart(pg_checkout,real_cache,monkeypatch,changed,legacy):
    sessions,uid,pid,_,orchestrator,payload=pg_checkout
    cache,_=real_cache
    key=f'ai_cart:{uid}'
    original={'items':[{'product_id':pid,'name':'Shoes','price':'10.50','quantity':2}]}
    await cache.set_json_required(key,original)
    broker=AsyncMock()
    broker.publish.return_value=PublishOutcome(PublishResult.CONFIRMED,'test','test',1,1.0)
    async with sessions() as db:
        result=await AICheckoutService(db,cache,broker,orchestrator).handle_confirm_order(payload)
        assert result['status']=='ready'
        order=await db.get(Order,result['order_id'])
        assert order.checkout_data['cart_snapshot']==original
        transaction=order.payment_transaction_id
        if legacy:
            order.checkout_data={k:v for k,v in order.checkout_data.items() if k!='cart_snapshot'}
            db.add(order);await db.commit()
    newer=copy.deepcopy(original)
    if changed:
        newer['items'][0]['quantity']=3
        await cache.set_json_required(key,newer)
    from app.services import payment_completion_service as module
    monkeypatch.setattr(module.gamification_service,'award_points_for_purchase',AsyncMock())
    async with sessions() as db:
        await PaymentCompletionService(db,broker,cache).finalize_successful_payment(result['order_id'],uid,transaction)
    assert await cache.get_json_required(key)==(newer if changed else None)
    async with sessions() as db:
        order=await db.get(Order,result['order_id'])
        assert order.is_paid
    assert broker.publish.await_count==3
    # A duplicated callback must not clear a fresh cart after the first commit.
    await cache.set_json_required(key,newer)
    async with sessions() as db:
        await PaymentCompletionService(db,broker,cache).finalize_successful_payment(result['order_id'],uid,transaction)
    assert await cache.get_json_required(key)==newer
    assert broker.publish.await_count==3
