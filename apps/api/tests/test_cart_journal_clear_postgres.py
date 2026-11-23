"""Clear, replay receipt and pending-order cancellation share one SQL commit."""
import os
from uuid import uuid4
import pytest
from sqlmodel import select
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.cart_journal_service import CartJournalService
from tests.test_saved_list_journal_postgres import saved_db
from tests.test_checkout_postgres import pg_checkout

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires disposable migrated PostgreSQL')

@pytest.mark.asyncio
async def test_clear_receipt_and_pending_order_cancellation_rollback_together(saved_db):
    sessions,uid,_=saved_db;identity=str(uuid4())
    async with sessions() as db:
        pending=Order(user_id=uid,total_price=21,status=OrderStatus.PENDING,delivery_address='Test')
        db.add(pending);await db.commit();oid=pending.id
        result=await CartJournalService(db).clear_cart(uid,identity,1)
        assert result['cart']['items']==[]
        await db.rollback()
    async with sessions() as db:
        assert (await db.get(Order,oid)).status==OrderStatus.PENDING
        assert (await CartJournalService(db).read_snapshot(uid))['revision']==1
        result=await CartJournalService(db).clear_cart(uid,identity,1)
        assert not result['replayed'];await db.commit()
    async with sessions() as db:
        assert (await db.get(Order,oid)).status==OrderStatus.CANCELLED
        replay=await CartJournalService(db).clear_cart(uid,identity,1)
        assert replay['replayed'] and replay['revision']==2
        await db.commit()

@pytest.mark.asyncio
async def test_replayed_clear_preserves_newer_cart_and_new_pending_order(saved_db):
    sessions,uid,pid=saved_db;identity=str(uuid4())
    async with sessions() as db:
        await CartJournalService(db).clear_cart(uid,identity,1);await db.commit()
    async with sessions() as db:
        svc=CartJournalService(db)
        await svc.apply_snapshot(uid,str(uuid4()),{'op':'add'},2,
            {'items':[{'product_id':pid,'name':'Shoes','quantity':1,'price':'10.50'}]})
        new_order=Order(user_id=uid,total_price=10.5,status=OrderStatus.PENDING,delivery_address='Test')
        db.add(new_order);await db.commit();oid=new_order.id
    async with sessions() as db:
        result=await CartJournalService(db).clear_cart(uid,identity,1)
        assert result['replayed'] and result['revision']==3 and len(result['cart']['items'])==1
        assert (await db.get(Order,oid)).status==OrderStatus.PENDING
        await db.commit()
