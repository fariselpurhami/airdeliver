"""CAP08 actual current SQL fallback and controlled vector outage."""
import os
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import delete,text,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_commerce_engine import AICommerceEngine,ValidationError

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
async def test_alternatives_vector_outage_sql_price_category_exclusion_and_current_change():
    native=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(native,expire_on_commit=False);ids=[]
    try:
        category='alternative-'+uuid4().hex
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name='Anchor or alternative',description='',category=category,price=price,inventory=5,is_active=active,rating=4.5) for price,active in [(100,True),(80,True),(69,True),(131,True),(90,False),(90,True)]]
            rows[-1].category='other-'+category
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        class Unavailable:
            def query(self,*args,**kwargs):raise ConnectionError('controlled vector outage')
        engine=AICommerceEngine(opensearch_client=object(),milvus_client=Unavailable(),embedding_model=object())
        engine.bootstrap=AsyncMock();engine.perform_hybrid_search_pure=AsyncMock(return_value=[])
        async with sessions() as db:
            result=await engine.find_genius_alternatives(db,ids[0],3)
            assert [p.id for p in result]==[ids[1]]
        async with sessions() as db:
            await db.execute(update(Product).where(Product.id==ids[1]).values(price=140));await db.commit()
        async with sessions() as db:
            assert await engine.find_genius_alternatives(db,ids[0],3)==[]
            assert await engine.find_genius_alternatives(db,2147483647,3)==[]
            with pytest.raises(ValidationError):await engine.find_genius_alternatives(db,0,3)
            with pytest.raises(ValidationError):await engine.find_genius_alternatives(db,ids[0],0)
        assert engine.perform_hybrid_search_pure.await_count==2
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await native.dispose()
