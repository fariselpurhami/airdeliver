"""Opening model copy, actual NLU/SQL/Redis publication, no provider calls."""
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete, update, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import AINLUService, MatrixConfig
from app.services.opening_sales_service import write_opening
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','price_changed','offline','rejected','one_paragraph','demo','empty'])
async def test_opening_model_insight_and_current_cards_through_real_publication(real_cache, mode):
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name='Catalog case',description='',category='accessories',price=20,inventory=10,currency='USD',attributes={'material':'cotton'})]
            if mode=='demo':rows[0].attributes={'_seed_dataset':'airdeliver-demo-v1'}
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
            for row in rows:await db.refresh(row)
        calls=[];published=[]
        async def infer(messages):
            data=json.loads(messages[1]['content']);calls.append(data)
            if mode=='offline':raise ConnectionError('controlled transport failure')
            if 'catalog_evidence' in data:
                if mode=='price_changed':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(price=30));await writer.commit()
                intro='Explore the current local catalog selection.'
                insight='Consider the listed material in the card before deciding. Merchant availability is unverified.'
                return json.dumps({'text':intro+(' ' if mode=='one_paragraph' else '\n\n')+insight,'product_ids':[],'claims':[]})
            return json.dumps(dict(supported=mode!='rejected',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        async def capture(channel,payload):published.append(json.loads(payload))
        cache.publish=capture
        async with sessions() as db:
            from app.services.free_llm_service import FreeLLMService
            llm=object.__new__(FreeLLMService);llm.__init__();llm.infer_sales_json=infer
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),cache,llm)
            svc.config=MatrixConfig(stream_delay_sec=0)
            svc.freshness_repo=SimpleNamespace(get_seen_product_ids=AsyncMock(return_value=set()),mark_products_as_seen=AsyncMock())
            svc._fetch_personal=AsyncMock(return_value=[] if mode=='empty' else rows)
            svc._fetch_bestsellers=AsyncMock(return_value=[]);svc._fetch_trending=AsyncMock(return_value=[]);svc._fetch_deals=AsyncMock(return_value=[])
            await svc._handle_initial_suggestions(3)
        if mode=='ok':
            assert len(published)==1 and published[0]['type']=='proactive_suggestion'
            assert published[0]['content']=='Explore the current local catalog selection.'
            assert published[0]['reason'].startswith('Consider the listed material')
            assert published[0]['products'][0]['price']=='20.00'
            assert calls[0]['request_evidence']['sales_intent']=='OPENING_INSIGHT'
            assert len(calls)==2
        else:
            assert not any(p.get('products') for p in published)
            assert published and published[0]['type'] in {'info','error'}
            if mode in {'demo','empty'}:assert calls==[]
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
