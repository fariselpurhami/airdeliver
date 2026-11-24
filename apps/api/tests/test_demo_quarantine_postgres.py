import json,os
from uuid import uuid4
import pytest
from sqlalchemy import select,delete,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from scripts.quarantine_demo_catalog import change,snapshot,encoded

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_quarantine_rollback_and_concurrent_edit_refusal_preserve_rows(tmp_path):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku='ADL-DEMO-v1-'+uuid4().hex,name='Synthetic test',category='test',description='',price=1,inventory=3),Product(sku=uuid4().hex,name='Real test',category='test',description='',price=1,inventory=3)]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async with engine.connect() as connection:
            before=await snapshot(connection);database=(await connection.execute(text('SELECT current_database()'))).scalar_one()
        manifest=tmp_path/'plan.json';manifest.write_text(json.dumps({'version':1,'database':database,'restore_database':'isolated_test_copy','backup_sha256':'test-only-verification-placeholder','before':before},default=str))
        await change(engine,manifest)
        async with sessions() as db:
            a,b=[await db.get(Product,pid) for pid in ids]
            assert not a.is_active and b.is_active
            assert a.inventory==3 and a.sku.startswith('ADL-DEMO-v1-')
        await change(engine,manifest,rollback=True)
        async with sessions() as db:
            assert (await db.get(Product,ids[0])).is_active
        with pytest.raises(ValueError):await change(engine,manifest)
        # New plan becomes stale after concurrent catalog edit, nothing changed.
        async with engine.connect() as connection:before=await snapshot(connection)
        stale=tmp_path/'stale.json';stale.write_text(json.dumps({'version':1,'database':database,'restore_database':'isolated_test_copy','backup_sha256':'test-only','before':before},default=str))
        async with engine.begin() as connection:await connection.execute(text('UPDATE products SET is_active=false WHERE id=:id'),{'id':ids[0]})
        with pytest.raises(ValueError):await change(engine,stale)
        async with sessions() as db:assert (await db.get(Product,ids[1])).is_active
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
