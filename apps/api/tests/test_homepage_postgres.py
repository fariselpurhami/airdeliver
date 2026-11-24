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
