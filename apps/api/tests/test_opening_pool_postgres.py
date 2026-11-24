import os
from uuid import uuid4
import pytest
from sqlalchemy import delete,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import AINLUService,MatrixConfig

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
async def test_eligible_rows_below_old_limit_survive_and_rating_uses_real_scale():
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku='ADL-DEMO-v1-'+uuid4().hex,name='Demo',description='',price=1,inventory=5,rating=5) for _ in range(105)]
            real=Product(sku=uuid4().hex,name='Real catalog belt',description='',price=20,inventory=3,rating=4.5,currency='USD')
            rows.append(real);db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        async with sessions() as db:
            service=object.__new__(AINLUService);service.db=db;service.config=MatrixConfig()
            assert service.config.deals_min_rating==4
            for method in [service._fetch_bestsellers,service._fetch_trending,service._fetch_deals]:
                result=await method(set())
                assert real.id in [r.id for r in result]
                assert not any(r.sku.startswith('ADL-DEMO-v1-') for r in result)
                assert real.id not in [r.id for r in await method({real.id})]
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_owner_pool_diagnostic_is_read_only_and_prints_counts(monkeypatch,capsys):
    import importlib.util
    from types import SimpleNamespace
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('inspect_pools',Path(__file__).resolve().parents[1]/'scripts/inspect_opening_pools.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'get_core_settings',lambda:SimpleNamespace(REDIS_URL=None,DATABASE_URI=os.environ['TEST_POSTGRES_DSN']))
    await module.inspect(3)
    import json
    output=json.loads(capsys.readouterr().out)
    assert output['user_id']==3 and output['redis_status']=='unconfigured'
    assert 'total' in output['catalog_counts']
    assert output['caveat'].startswith('Counts reproduce')
