"""Real PostgreSQL and Redis reconciliation boundary, not fake persistence."""
import os
from uuid import uuid4
import pytest
from unittest.mock import AsyncMock
from app.services.cart_journal_service import CartJournalService
from app.services.cart_reconciliation_service import CartReconciliationService
from tests.test_cart_journal_postgres import journal_db, STATE
from tests.test_customer_memory_postgres import memory_db
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires disposable migrated PostgreSQL')

@pytest.mark.asyncio
async def test_missing_stale_corrupt_and_cache_loss_rebuild_only_from_sql(journal_db,real_cache):
    sessions,(uid,_)=journal_db;cache,_=real_cache;key=f'canonical_cart:v1:{uid}'
    async with sessions() as db:
        svc=CartReconciliationService(db,cache)
        await cache.set_json_required(f'ai_cart:{uid}',{'items':['legacy untouched']})
        assert (await svc.reconcile(uid))['status']=='uninitialized'
        assert await cache.get_json_required(key) is None
        await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'seed'},0,STATE);await db.commit()
        for cached in [None,{'revision':0,'items':[]},{'revision':1,'items':['corrupt']}]:
            if cached is None:await cache.delete_required(key)
            else:await cache.set_json_required(key,cached)
            result=await svc.reconcile(uid)
            assert result['status']=='repaired' and result['cart']['revision']==1
            assert result['cart']['items'][0]['quantity']==2
        assert (await svc.reconcile(uid))['status']=='current'
        await cache.client.flushdb()
        assert (await svc.reconcile(uid))['status']=='repaired'
        # SQL remains committed after complete loss of cached state.
        assert (await CartJournalService(db).read_snapshot(uid))['total']=='39.98'

@pytest.mark.asyncio
async def test_concurrent_newer_cache_and_outage_never_overwrite_or_erase_sql(journal_db,real_cache):
    sessions,(uid,_)=journal_db;cache,_=real_cache;key=f'canonical_cart:v1:{uid}'
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'seed'},0,STATE);await db.commit()
        svc=CartReconciliationService(db,cache)
        await cache.set_json_required(key,{'revision':2,'items':[]})
        assert (await svc.reconcile(uid))['status']=='retry'
        assert (await cache.get_json_required(key))['revision']==2
        cache.get_json_required=AsyncMock(side_effect=ConnectionError('offline'))
        result=await svc.reconcile(uid)
        assert result['status']=='cache_unavailable' and result['cart']['revision']==1

@pytest.mark.asyncio
async def test_competing_cache_publication_cannot_be_replaced_by_old_repair(journal_db,real_cache):
    sessions,(uid,_)=journal_db;cache,_=real_cache;key=f'canonical_cart:v1:{uid}'
    async with sessions() as db:
        await CartJournalService(db).apply_snapshot(uid,str(uuid4()),{'op':'seed'},0,STATE);await db.commit()
        original=cache.compare_json_required
        async def racing_compare(*args,**kwargs):
            await cache.set_json_required(key,{'revision':2,'items':[]})
            return await original(*args,**kwargs)
        cache.compare_json_required=racing_compare
        result=await CartReconciliationService(db,cache).reconcile(uid)
        assert result['status']=='retry'
        assert (await cache.get_json_required(key))['revision']==2
