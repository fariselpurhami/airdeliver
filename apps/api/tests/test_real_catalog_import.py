"""Actual SQL contract plus explicit local fixture isolation."""
import os,uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select,text
from app.services import catalog_visibility as visibility
from app.services.real_catalog_import import ImportFile,ImportRow,persist_import,sync_import
from scripts.generate_dev_catalog import generate

@pytest.fixture
def fixture_mode(monkeypatch):
    monkeypatch.setattr(visibility,'fixtures_enabled',lambda:True)

def test_generate_1000_unique_taxonomy_provenance_and_bounded_values(fixture_mode):
    payload=ImportFile.model_validate(generate())
    assert len(payload.products)==1000
    assert len({r.sku for r in payload.products})==1000
    assert set(r.category for r in payload.products)==set( __import__('app.services.real_catalog_import',fromlist=['CATEGORIES']).CATEGORIES)
    assert all(r.rating is None and r.image_url==f'/dev-fixtures/{r.category}.svg' for r in payload.products)

def test_fixture_flag_off_production_and_legacy_demo_excluded(monkeypatch,fixture_mode):
    item=SimpleNamespace(sku='ADL-DEV-v1-clothing-0001',attributes={'_seed_dataset':visibility.FIXTURE_DATASET})
    assert visibility.is_synthetic(item) and not visibility.is_catalog_hidden(item)
    monkeypatch.setattr(visibility,'fixtures_enabled',lambda:False)
    assert visibility.is_catalog_hidden(item)
    with pytest.raises(ValueError):generate()
    assert visibility.is_catalog_hidden(SimpleNamespace(sku='ADL-DEMO-v1-1',attributes={}))

def test_production_config_cannot_enable_flag(monkeypatch):
    from app.core.config import get_core_settings,CoreSettings
    existing=get_core_settings().model_dump();existing['AIRDELIVER_DEV_FIXTURES']=True;existing['APP_ENV']='production'
    with pytest.raises(ValueError,match='forbidden'):CoreSettings(_env_file=None,**existing)
    existing['APP_ENV']='development';monkeypatch.setenv('NODE_ENV','production')
    with pytest.raises(ValueError,match='forbidden'):CoreSettings(_env_file=None,**existing)

def test_duplicate_sku_real_masquerade_bad_category_and_inventory(fixture_mode):
    raw=generate(2);raw['products'][1]['sku']=raw['products'][0]['sku']
    with pytest.raises(ValueError):ImportFile.model_validate(raw)
    raw=generate(1);raw['source_kind']='partner_feed';raw['authorised_source_url']='https://merchant.shop/feed'
    with pytest.raises(ValueError):ImportFile.model_validate(raw)
    for field,value in [('category','phones'),('inventory',True),('price','nan'),('image_url','http://127.0.0.1/x')]:
        row=generate(1)['products'][0];row[field]=value
        with pytest.raises(ValueError):ImportRow.model_validate(row)

@pytest.mark.asyncio
async def test_actual_pg_idempotent_sku_update_and_foreign_source_guard(fixture_mode):
    if not os.environ.get('TEST_POSTGRES_DSN'):pytest.skip('Disposable PostgreSQL required')
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.models.product import Product
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);factory=async_sessionmaker(engine,expire_on_commit=False)
    raw=generate(7);suffix=uuid.uuid4().hex[:8]
    for row in raw['products']:row['sku']+='-'+suffix
    payload=ImportFile.model_validate(raw)
    try:
        async with factory() as db:
            rows,report=await persist_import(db,payload);ids=[r['id'] for r in rows];assert report['create']==7
            payload.products[0].inventory=12
            repeated,report=await persist_import(db,payload)
            assert [r['id'] for r in repeated]==ids and report['create']==0 and repeated[0]['inventory']==12
            assert all(r['attributes']['_seed_dataset']==visibility.FIXTURE_DATASET for r in repeated)
            victim=await db.get(Product,ids[0]);victim.attributes={'_import_source_id':'other-source'};await db.commit()
            with pytest.raises(ValueError,match='another source'):await persist_import(db,payload)
            await db.rollback()
            remaining=(await db.execute(select(Product).where(Product.id.in_(ids)))).scalars().all();assert len(remaining)==7
            # Isolated testcleanup only, never exposed by importer.
            for row in remaining:await db.delete(row)
            await db.commit()
    finally:await engine.dispose()

@pytest.mark.asyncio
async def test_reviewed_sinks_confirm_counts_nondestructive_and_fail_partial(fixture_mode):
    row=generate(1)['products'][0]
    snapshot={**row,'id':123,'image':row['image_url'],'is_active':True,'rating':None}
    embedding=SimpleNamespace(dimension=2,embed_products=AsyncMock(return_value=[[1.,0.]]))
    m=SimpleNamespace(initialize_schema=AsyncMock(),insert_batch=AsyncMock(return_value=1))
    o=SimpleNamespace(initialize_schema=AsyncMock(),insert_batch=AsyncMock(return_value=1))
    assert await sync_import([snapshot],embedding,m,o)=={'milvus':1,'opensearch':1}
    m.initialize_schema.assert_awaited_once_with(2,drop_existing=False)
    assert m.insert_batch.await_args.args[0][0].id==123
    o.insert_batch.return_value=0
    with pytest.raises(RuntimeError):await sync_import([snapshot],embedding,m,o)

@pytest.mark.asyncio
async def test_fixture_actual_sql_opening_pools_and_normal_cart_policy(fixture_mode):
    if not os.environ.get('TEST_POSTGRES_DSN'):pytest.skip('Disposable PostgreSQL required')
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.services.ai_nlu_service import AINLUService,MatrixConfig
    from app.services.shopping_discovery import catalog_result
    from app.services.opening_catalog_status import opening_catalog_status
    from app.models.product import Product
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);factory=async_sessionmaker(engine,expire_on_commit=False)
    payload=ImportFile.model_validate(generate(7));ids=[]
    for r in payload.products:r.sku+='-'+uuid.uuid4().hex[:6]
    try:
        async with factory() as db:
            baseline=await opening_catalog_status(db,set())
            rows,_=await persist_import(db,payload);ids=[r['id'] for r in rows]
            service=object.__new__(AINLUService);service.db=db;service.config=MatrixConfig()
            for method in [service._fetch_bestsellers,service._fetch_trending,service._fetch_deals]:
                result=await method(set());assert set(ids)<=set(r.id for r in result)
            p=await db.get(Product,ids[0]);card=catalog_result(p)
            assert card.evidence_kind=='dev_fixture' and card.stock_status=='fixture_in_stock'
            assert not visibility.is_catalog_hidden(p) and visibility.is_synthetic(p)
            status=await opening_catalog_status(db,set());assert status['dev_fixtures']>=7
            assert status['real_eligible']==baseline['real_eligible']
    finally:
        async with factory() as db:
            for id in ids:
                row=await db.get(Product,id)
                if row:await db.delete(row)
            await db.commit()
        await engine.dispose()

def test_fixture_no_popularity_urgency_discount_copy(fixture_mode):
    from app.services.shopping_copy import ShoppingDraft,validate_draft
    from app.services.shopping_discovery import catalog_result
    row=generate(1)['products'][0]
    product=SimpleNamespace(**{**row,'id':1,'is_active':True,'image':row['image_url'],'attributes':{'_seed_dataset':visibility.FIXTURE_DATASET}})
    card=catalog_result(product)
    assert card.evidence_kind=='dev_fixture'
    for copy in ['This is a popular choice.','Hurry, limited stock.','A discount today.','Our bestseller.']:
        with pytest.raises(ValueError,match='fixture_claim'):validate_draft(ShoppingDraft(text=copy,product_ids=[],claims=[]),[card])

@pytest.mark.asyncio
async def test_fixture_normal_cart_add_uses_persisted_product_with_actual_redis(fixture_mode,real_cache):
    if not os.environ.get('TEST_POSTGRES_DSN'):pytest.skip('Disposable PostgreSQL required')
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.services.ai_cart_service import AICartService
    from app.models.product import Product
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);factory=async_sessionmaker(engine,expire_on_commit=False)
    payload=ImportFile.model_validate(generate(1));payload.products[0].sku+='-'+uuid.uuid4().hex[:8];ids=[];cache,_=real_cache
    try:
        async with factory() as db:
            rows,_=await persist_import(db,payload);ids=[r['id'] for r in rows]
            service=AICartService(db,cache,object())
            await service.handle_add_to_cart({'user_id':987654,'product_id':ids[0],'quantity':2})
            saved=await cache.get_json_required(service._get_cart_key(987654))
            assert saved['items'][0]['product_id']==ids[0] and saved['items'][0]['quantity']==2
            assert str(saved['items'][0]['price'])==payload.products[0].price
    finally:
        async with factory() as db:
            for id in ids:
                row=await db.get(Product,id)
                if row:await db.delete(row)
            await db.commit()
        await engine.dispose()

from tests.test_cart_persistence_outcomes import real_cache

@pytest.mark.asyncio
async def test_all1000_rows_actual_sql_twice_and_flagoff_exclusion(fixture_mode,monkeypatch):
    if not os.environ.get('TEST_POSTGRES_DSN'):pytest.skip('Disposable PostgreSQL required')
    from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
    from app.models.product import Product
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);factory=async_sessionmaker(engine,expire_on_commit=False)
    payload=ImportFile.model_validate(generate());suffix=uuid.uuid4().hex[:6];ids=[]
    for row in payload.products:row.sku+='-'+suffix
    try:
        async with factory() as db:
            first,report=await persist_import(db,payload);ids=[p['id'] for p in first]
            second,report=await persist_import(db,payload)
            assert len(set(ids))==1000 and [p['id'] for p in second]==ids and report['create']==0
            assert set(p['category'] for p in first)==set(__import__('app.services.real_catalog_import',fromlist=['CATEGORIES']).CATEGORIES)
            visible=(await db.execute(select(Product.id).where(Product.id.in_(ids),*visibility.real_catalog_predicates(Product)))).scalars().all()
            assert set(visible)==set(ids)
            monkeypatch.setattr(visibility,'fixtures_enabled',lambda:False)
            hidden=(await db.execute(select(Product.id).where(Product.id.in_(ids),*visibility.real_catalog_predicates(Product)))).scalars().all()
            assert hidden==[]
            assert (await db.execute(select(Product.id).where(Product.id.in_(ids)))).scalars().all()
    finally:
        from sqlalchemy import delete
        async with factory() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
