"""Customer catalog surfaces hide synthetic rows without changing stored history."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import delete,select
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.api.v1.endpoints.products import read_products,get_featured_recommendation

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_list_filters_before_limit_and_keeps_both_synthetic_markers():
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[];category=uuid4().hex
    try:
        async with sessions() as db:
            rows=[Product(sku='ADL-DEMO-v1-'+uuid4().hex if i==0 else uuid4().hex,name='Catalog item',category=category,description='',price=20,inventory=1,attributes={'_seed_dataset':'airdeliver-demo-v1'} if i==1 else {}) for i in range(3)]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
            data=await read_products(db=db,skip=0,limit=1,page=None,category=category)
            assert len(data)==1 and data[0]['id']==ids[2]
            retained=(await db.execute(select(Product).where(Product.id.in_(ids)))).scalars().all()
            assert len(retained)==3 and {p.id:p for p in retained}[ids[1]].attributes['_seed_dataset']=='airdeliver-demo-v1'
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
