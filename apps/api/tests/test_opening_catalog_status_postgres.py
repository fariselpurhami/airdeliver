import os
from uuid import uuid4
import pytest
from sqlalchemy import text,delete
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.opening_catalog_status import opening_catalog_status,opening_status_notice
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable migratedPG required')

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['empty','demo','inactive','nostock','currency','ok','recent'])
async def test_exact_catalog_reason_real_sql(mode):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            # Own transaction rolled back; no data outside disposable test DB.
            await db.execute(delete(Product))
            row=None
            if mode!='empty':
                row=Product(sku=('ADL-DEMO-v1-' if mode=='demo' else '')+uuid4().hex,name='Real source product',description='',price=20,currency='bad' if mode=='currency' else 'USD',inventory=0 if mode=='nostock' else 3,is_active=mode!='inactive')
                db.add(row);await db.flush()
            result=await opening_catalog_status(db,{row.id} if mode=='recent' else set())
            expected={'empty':'catalog_empty','demo':'demo_only_catalog','inactive':'no_real_eligible_stock','nostock':'no_real_eligible_stock','currency':'no_real_eligible_stock','ok':'eligible_pool_not_published','recent':'all_real_cards_recent'}[mode]
            assert result['reason']==expected
            assert opening_status_notice(result).startswith('System notice:')
            await db.rollback()
    finally:await engine.dispose()
