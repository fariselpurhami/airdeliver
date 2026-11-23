"""Prepared SQL saved-list commit/receipt/cart clear share one transaction."""
import asyncio
from decimal import Decimal
import os
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlmodel import select
from app.models.cart_journal import CustomerCartState,CartMutationRecord
from app.models.order import Order,OrderItem
from app.services.cart_journal_service import CartJournalService
from tests.test_checkout_postgres import pg_checkout

pytestmark=pytest.mark.skipif(not os.getenv("TEST_POSTGRES_DSN"),reason="requires disposable migrated PostgreSQL")


@pytest_asyncio.fixture
async def saved_db(pg_checkout):
    sessions,uid,pid,*_=pg_checkout
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'seed'},0,
            {'items':[{'product_id':pid,'name':'Shoes','price':'10.50','quantity':2}]})
        await db.commit()
    yield sessions,uid,pid
    async with sessions() as db:
        await db.execute(delete(CartMutationRecord).where(CartMutationRecord.user_id==uid))
        await db.execute(delete(CustomerCartState).where(CustomerCartState.user_id==uid))
        await db.commit()


@pytest.mark.asyncio
async def test_saved_list_replay_after_commit_creates_one_order_and_preserves_newer_cart(saved_db):
    sessions,uid,pid=saved_db;identity=str(uuid4())
    async with sessions() as db:
        first=await CartJournalService(db).save_list(uid,identity,1);await db.commit()
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'add'},2,
            {'items':[{'product_id':pid,'name':'Shoes','price':'10.50','quantity':1}]});await db.commit()
    async with sessions() as db:
        replay=await CartJournalService(db).save_list(uid,identity,1)
        assert replay['replayed'] and replay['outcome']==first['outcome']
        assert replay['revision']==3 and replay['cart']['items'][0]['quantity']==1
        orders=(await db.execute(select(Order).where(Order.user_id==uid))).scalars().all()
        assert len(orders)==1 and Decimal(str(orders[0].total_price))==Decimal('21.00')
        lines=(await db.execute(select(OrderItem).where(OrderItem.order_id==orders[0].id))).scalars().all()
        assert len(lines)==1 and lines[0].quantity==2
        await db.commit()


@pytest.mark.asyncio
async def test_two_independent_save_transactions_same_identity_create_one_list(saved_db):
    sessions,uid,_=saved_db;identity=str(uuid4())
    async def save():
        async with sessions() as db:
            result=await CartJournalService(db).save_list(uid,identity,1);await db.commit();return result
    results=await asyncio.gather(save(),save())
    assert sorted(r['replayed'] for r in results)==[False,True]
    assert results[0]['outcome']['saved_order_id']==results[1]['outcome']['saved_order_id']


@pytest.mark.asyncio
async def test_rollback_of_saved_order_also_rolls_back_cart_clear_and_receipt(saved_db):
    sessions,uid,_=saved_db;identity=str(uuid4())
    async with sessions() as db:
        await CartJournalService(db).save_list(uid,identity,1);await db.rollback()
    async with sessions() as db:
        assert (await db.execute(select(Order).where(Order.user_id==uid))).scalars().all()==[]
        cart=await CartJournalService(db).locked_state(uid)
        assert cart.revision==1 and cart.state['items'][0]['quantity']==2
        result=await CartJournalService(db).save_list(uid,identity,1)
        assert not result['replayed'];await db.commit()
