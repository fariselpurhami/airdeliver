"""Direct no-target entrypoint rechecks real SQL after writer/review awaits."""
import json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService
from app.services.shopping_discovery import ShoppingBrief

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')
@pytest.mark.asyncio
@pytest.mark.parametrize('change',['none','price','stock','spec','deleted'])
async def test_direct_search_actual_sql_postwriter_recheck(change):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);pid=None
    try:
        async with sessions() as db:
            row=Product(sku=uuid4().hex,name='Atlas laptop',description='',category='electronics',price=20,currency='USD',inventory=3,attributes={'RAM':'32GB'})
            db.add(row);await db.commit();pid=row.id
        async def retrieve(db,query,**kwargs):return (await db.execute(select(Product).where(Product.id==pid))).scalars().all()
        svc=object.__new__(NeuralCoreService);svc.ai_engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve));svc.is_healthy=True
        async def infer(messages):
            data=json.loads(messages[1]['content'])
            if 'catalog_evidence' in data:
                if change!='none':
                    async with sessions() as writer:
                        if change=='deleted':await writer.execute(delete(Product).where(Product.id==pid))
                        else:await writer.execute(update(Product).where(Product.id==pid).values(**{'price':{'price':30},'stock':{'inventory':0},'spec':{'attributes':{'RAM':'8GB'}}}[change]))
                        await writer.commit()
                return json.dumps({'text':'The card shows current catalog facts. Merchant availability is unverified.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=infer
        async with sessions() as db:result=await svc._handle_product_search(db,'Atlas laptop',ShoppingBrief(required_features=['at least 16GB RAM']),'Atlas laptop at least 16GB RAM')
        if change=='none':assert [c.id for c in result.products]==[pid]
        else:assert result.response_kind=='system_notice' and result.products==[]
    finally:
        async with sessions() as db:
            if pid:await db.execute(delete(Product).where(Product.id==pid));await db.commit()
        await engine.dispose()
