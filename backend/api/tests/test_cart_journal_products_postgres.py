"""Canonical add/remove use fresh PG catalog and durable receipts."""
import os
import asyncio
from decimal import Decimal
from uuid import uuid4
import pytest
from app.models.product import Product
from app.services.cart_journal_service import CartJournalService,CartJournalConflict
from tests.test_saved_list_journal_postgres import saved_db
from tests.test_checkout_postgres import pg_checkout

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires disposable migrated PostgreSQL')

@pytest.mark.asyncio
async def test_add_refreshes_price_then_replay_survives_catalog_unavailability(saved_db):
    sessions,uid,pid=saved_db;identity=str(uuid4())
    async with sessions() as db:
        product=await db.get(Product,pid);product.price=12;db.add(product);await db.commit()
        result=await CartJournalService(db).mutate_product(uid,identity,'add',pid,1,1)
        assert result['cart']['items'][0]['quantity']==3 and Decimal(result['cart']['total'])==Decimal('36.00')
        await db.commit()
        product.is_active=False;db.add(product);await db.commit()
    async with sessions() as db:
        replay=await CartJournalService(db).mutate_product(uid,identity,'add',pid,1,1)
        assert replay['replayed'] and replay['revision']==2
        with pytest.raises(CartJournalConflict):
            await CartJournalService(db).mutate_product(uid,identity,'add',pid,2,2)
        await db.rollback()

@pytest.mark.asyncio
async def test_remove_replay_preserves_later_readdition(saved_db):
    sessions,uid,pid=saved_db;identity=str(uuid4())
    async with sessions() as db:
        svc=CartJournalService(db)
        await svc.mutate_product(uid,identity,'remove',pid,1,1);await db.commit()
        await svc.mutate_product(uid,str(uuid4()),'add',pid,1,2);await db.commit()
    async with sessions() as db:
        result=await CartJournalService(db).mutate_product(uid,identity,'remove',pid,1,1)
        assert result['replayed'] and result['revision']==3 and result['cart']['items'][0]['quantity']==1
        await db.commit()

@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[('inventory',2),('currency','EUR'),('is_active',False)])
async def test_rejected_product_mutation_writes_no_cart_or_receipt(saved_db,field,value):
    sessions,uid,pid=saved_db;identity=str(uuid4())
    async with sessions() as db:
        product=await db.get(Product,pid);setattr(product,field,value);db.add(product);await db.commit()
        with pytest.raises(ValueError):await CartJournalService(db).mutate_product(uid,identity,'add',pid,1,1)
        await db.rollback()
        assert (await CartJournalService(db).read_snapshot(uid))['revision']==1

@pytest.mark.asyncio
async def test_competing_different_add_ids_with_same_revision_cannot_lose_update(saved_db):
    from app.services.cart_journal_service import CartJournalStale
    sessions,uid,pid=saved_db
    async def add():
        async with sessions() as db:
            try:
                result=await CartJournalService(db).mutate_product(uid,str(uuid4()),'add',pid,1,1)
                await db.commit();return result
            except CartJournalStale:
                await db.rollback();return 'stale'
    results=await asyncio.gather(add(),add())
    assert sum(result=='stale' for result in results)==1
    async with sessions() as db:
        snapshot=await CartJournalService(db).read_snapshot(uid)
        assert snapshot['revision']==2 and snapshot['items'][0]['quantity']==3

@pytest.mark.asyncio
async def test_refresh_existing_line_preserves_original_cart_order(saved_db):
    sessions,uid,pid=saved_db
    async with sessions() as db:
        svc=CartJournalService(db)
        await svc.apply_snapshot(uid,str(uuid4()),{'op':'seed-second-line'},1,
            {'items':[{'product_id':pid,'name':'Shoes','quantity':2,'price':'10.50'},
                      {'product_id':pid+1000000,'name':'Other item','quantity':1,'price':'5.00'}]})
        await db.commit()
        result=await svc.mutate_product(uid,str(uuid4()),'add',pid,1,2)
        assert [line['product_id'] for line in result['cart']['items']]==[pid,pid+1000000]
        assert result['cart']['items'][0]['quantity']==3
        await db.commit()
