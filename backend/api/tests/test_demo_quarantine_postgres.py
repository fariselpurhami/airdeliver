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

@pytest.mark.asyncio
async def test_plan_requires_independent_database_and_matching_product_snapshots(tmp_path):
    from scripts.quarantine_demo_catalog import make_plan
    from sqlalchemy.engine import make_url
    from sqlalchemy import update
    from sqlalchemy.pool import NullPool
    url=make_url(os.environ['TEST_POSTGRES_DSN'])
    assert url.database.startswith('airdeliver_test_')
    admin=create_async_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT',poolclass=NullPool)
    target='airdeliver_test_plan_'+uuid4().hex[:12]
    engine=create_async_engine(url);restored=None;created=False;ids=[]
    archive=tmp_path/'archive.dump';archive.write_bytes(b'controlled archive identity, no restore claim')
    try:
        async with admin.connect() as connection:
            # Test-only isolated database, never an existing target.
            await connection.execute(text('CREATE DATABASE "'+target+'" TEMPLATE "'+url.database+'"'))
            created=True
        restored=create_async_engine(url.set(database=target))
        with pytest.raises(ValueError,match='different database'):
            await make_plan(engine,engine,archive,tmp_path/'same.json')
        manifest=tmp_path/'matching.json'
        assert await make_plan(engine,restored,archive,manifest)>=0
        assert manifest.stat().st_mode & 0o777==0o600
        data=json.loads(manifest.read_text())
        import hashlib
        assert data['backup_sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
        assert data['database']!=data['restore_database']
        with pytest.raises(ValueError,match='overwrite'):
            await make_plan(engine,restored,archive,manifest)
        async with restored.begin() as connection:
            await connection.execute(text("INSERT INTO products(sku,name,description,price,currency,inventory,category,tags,attributes,is_active,created_at,updated_at) VALUES (:sku,'Restored-only row','',1,'USD',1,'test','[]','{}',true,now(),now())"),{'sku':uuid4().hex})
        with pytest.raises(ValueError,match='does not match'):
            await make_plan(engine,restored,archive,tmp_path/'different.json')
        assert not (tmp_path/'different.json').exists()
    finally:
        await engine.dispose()
        if restored:await restored.dispose()
        if created:
            async with admin.connect() as connection:
                await connection.execute(text('DROP DATABASE "'+target+'"'))
        await admin.dispose()
