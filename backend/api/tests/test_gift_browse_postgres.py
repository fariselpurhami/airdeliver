"""Owner optionA, actualSQL/cards/writer/review/currentrow publication."""
import json,os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService
from app.services.shopping_discovery import ShoppingBrief
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='Disposable PostgreSQL required')

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','missing_budget','changed_price','review_reject'])
async def test_budget_occasion_browse_diversity_hardcap_and_revalidation(mode):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=category+' catalog option',description='',category=category,price=price,currency=currency,inventory=stock,attributes=attrs) for category,price,currency,stock,attrs in [
                ('bags',20,'USD',2,{}),('jewelry',30,'USD',2,{}),('care',40,'USD',2,{}),('expensive',200,'USD',2,{}),('wrongcurrency',20,'EUR',2,{}),('outofstock',10,'USD',0,{}),('demo',10,'USD',2,{'_seed_dataset':'airdeliver-demo-v1'})]]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        svc=object.__new__(NeuralCoreService);svc.is_healthy=True;svc.ai_engine=SimpleNamespace()
        brief=ShoppingBrief(occasion='birthday',budget='$150',budget_max='150',budget_currency='USD')
        if mode=='missing_budget':brief=ShoppingBrief(occasion='birthday')
        seen=[]
        async def infer(messages):
            payload=json.loads(messages[1]['content']);seen.append(payload)
            if 'catalog_evidence' in payload:
                if mode=='changed_price':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(price=300));await writer.commit()
                return json.dumps({'text':'Explore these different catalog categories within your stated budget. Which category would you like to explore?','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=mode!='review_reject',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=infer
        async with sessions() as db:result=await svc._handle_gift_browse(db,'A birthday gift under $150',brief)
        if mode=='ok':
            assert len({p.category for p in result.products})>=3
            assert all(p.currency=='USD' and Decimal(p.price)<=150 and p.stock_status=='local_in_stock' for p in result.products)
            assert not any(p.category in {'expensive','wrongcurrency','outofstock','demo'} for p in result.products)
            assert seen[0]['request_evidence']['gift_browse'] and result.text.count('?')==1
        elif mode=='missing_budget':assert result.response_kind=='clarification' and not result.products
        else:assert result.response_kind=='system_notice' and not result.products
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
