"""CAP07 SQL fallback/tier boundary. No embedding or provider calls."""
import os
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import delete,text,select
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
async def test_homepage_sql_fallback_tiers_and_seen_exclusions():
    native=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(native,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            existing=list((await db.execute(select(Product.id))).scalars())
            rows=[Product(sku=uuid4().hex,name='Homepage '+str(i),description='',price=i+1,inventory=5,rating=5-i*.1) for i in range(25)]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        engine=AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object())
        engine.bootstrap=AsyncMock();engine.perform_hybrid_search_pure=AsyncMock(return_value=[])
        async with sessions() as db:
            low=await engine.get_fresh_homepage_matrix(db,3,existing+[ids[0]],'LOW')
            high=await engine.get_fresh_homepage_matrix(db,3,existing+[ids[-1]],'HIGH')
            invalid=await engine.get_fresh_homepage_matrix(db,3,existing,'invalid-tier')
            assert {r.id for r in low}==set(ids[1:9])
            assert {r.id for r in high}==set(ids[-9:-1])
            assert {r.id for r in invalid}==set(ids[:8])
            assert len({r.id for r in low})==8
            assert await engine.get_fresh_homepage_matrix(db,3,existing+ids,'LOW')==[]
        assert engine.perform_hybrid_search_pure.await_count==4
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await native.dispose()

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['synthetic_prefix','seen_index','stale_index','duplicate_index','outage','cancel'])
async def test_homepage_actual_current_sql_never_recycles_ineligible_index_rows(mode):
    import asyncio
    from sqlalchemy import update
    native=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(native,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            existing=list((await db.execute(select(Product.id))).scalars())
            rows=[Product(sku='ADL-DEMO-v1-'+uuid4().hex,name='Synthetic',description='',price=1,inventory=5,currency='USD',rating=5) for _ in range(65)]
            rows += [Product(sku=uuid4().hex,name='Eligible '+str(i),description='',price=10+i,inventory=3,currency='USD',rating=4) for i in range(10)]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows];real=rows[-10:]
        engine=AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object());engine.bootstrap=AsyncMock()
        seen=existing+[real[0].id]
        if mode=='stale_index':
            async with sessions() as db:await db.execute(update(Product).where(Product.id==real[1].id).values(inventory=0));await db.commit()
        engine.perform_hybrid_search_pure=AsyncMock(return_value=[real[0]] if mode=='seen_index' else [real[1],real[1]] if mode=='duplicate_index' else real[:2] if mode=='stale_index' else [])
        if mode in {'outage','cancel'}:engine.perform_hybrid_search_pure.side_effect=ConnectionError() if mode=='outage' else asyncio.CancelledError()
        async with sessions() as db:
            if mode=='cancel':
                with pytest.raises(asyncio.CancelledError):await engine.get_fresh_homepage_matrix(db,17,seen,'LOW')
            else:
                result=await engine.get_fresh_homepage_matrix(db,17,seen,'LOW')
                if mode=='outage':assert result==[]
                else:
                    assert len(result)==8 and len({p.id for p in result})==8
                    assert {p.id for p in result}<=set(ids[-10:])-set(seen)
                    assert all(p.inventory>0 for p in result)
    finally:
        async with sessions() as db:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await native.dispose()
