"""Canonical SQL cart+receipt transaction, independent sessions and rollback."""
import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from app.models.cart_journal import CustomerCartState,CartMutationRecord
from app.services.cart_journal_service import CartJournalService,CartJournalConflict,CartJournalStale
from tests.test_customer_memory_postgres import memory_db


STATE={'items':[{'product_id':7,'name':'Shoes','quantity':2,'price':'19.99'}],'total':'0.00'}


@pytest_asyncio.fixture
async def journal_db(memory_db):
    sessions,users=memory_db
    yield sessions,users
    async with sessions() as db:
        await db.execute(delete(CartMutationRecord).where(CartMutationRecord.user_id.in_(users)))
        await db.execute(delete(CustomerCartState).where(CustomerCartState.user_id.in_(users)))
        await db.commit()


@pytest.mark.asyncio
async def test_new_session_after_commit_replays_receipt_and_never_reverts_newer_cart(journal_db):
    sessions,(uid,_)=journal_db;identity=str(uuid4())
    async with sessions() as db:
        first=await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add','id':7},0,STATE)
        await db.commit()
    async with sessions() as db:
        newer=await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'clear'},1,{'items':[]})
        await db.commit()
    async with sessions() as db:
        replay=await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add','id':7},0,STATE)
        assert replay['replayed'] and replay['outcome']['revision']==1
        assert replay['revision']==2 and replay['cart']['items']==[]
        await db.commit()
    assert first['cart']['total']=='39.98' and newer['revision']==2


@pytest.mark.asyncio
async def test_same_key_conflict_and_customer_isolation(journal_db):
    sessions,(uid,other)=journal_db;identity=str(uuid4())
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add'},0,STATE);await db.commit()
    async with sessions() as db:
        with pytest.raises(CartJournalConflict):
            await CartJournalService(db).apply_snapshot(uid,identity,{'op':'remove'},1,{'items':[]})
        await db.rollback()
        result=await CartJournalService(db).apply_snapshot(other,identity,{'op':'add'},0,STATE)
        assert result['revision']==1 and not result['replayed'];await db.commit()


@pytest.mark.asyncio
async def test_concurrent_same_identity_commits_once(journal_db):
    sessions,(uid,_)=journal_db;identity=str(uuid4())
    async def apply():
        async with sessions() as db:
            result=await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add'},0,STATE)
            await db.commit();return result
    results=await asyncio.gather(apply(),apply())
    assert sorted(r['replayed'] for r in results)==[False,True]
    assert all(r['revision']==1 for r in results)


@pytest.mark.asyncio
async def test_rollback_loses_neither_state_nor_receipt_separately(journal_db):
    sessions,(uid,_)=journal_db;identity=str(uuid4())
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add'},0,STATE)
        await db.rollback()
    async with sessions() as db:
        result=await CartJournalService(db).apply_snapshot(uid,identity,{'op':'add'},0,STATE)
        assert not result['replayed'] and result['revision']==1;await db.commit()
    async with sessions() as db:
        with pytest.raises(CartJournalStale):
            await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'clear'},0,{'items':[]})
        await db.rollback()
