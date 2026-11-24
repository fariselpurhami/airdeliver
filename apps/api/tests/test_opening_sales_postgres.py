"""Opening model copy, actual NLU/SQL/Redis publication, no provider calls."""
import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete, update, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import AINLUService, MatrixConfig, RedisKeys
from app.services.opening_sales_service import write_opening
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','price_changed','offline','rejected','one_paragraph','demo','demo_preview','demo_preview_seen','empty'])
async def test_opening_model_insight_and_current_cards_through_real_publication(real_cache, mode,caplog,monkeypatch):
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name='Catalog case',description='',category='accessories',price=20,inventory=10,currency='USD',attributes={'material':'cotton'})]
            if mode in {'demo','demo_preview','demo_preview_seen'}:rows[0].attributes={'_seed_dataset':'airdeliver-demo-v1'}
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
            for row in rows:await db.refresh(row)
        if mode in {'demo_preview','demo_preview_seen'}:
            from app.core.config import get_core_settings
            monkeypatch.setattr(get_core_settings(),'DEV_DEMO_CATALOG_PREVIEW',True)
        calls=[];published=[]
        subscriber=cache.client.pubsub()
        await subscriber.subscribe(RedisKeys.ui_channel(3))
        await subscriber.get_message(timeout=1)
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
        async with sessions() as db:
            from app.services.free_llm_service import FreeLLMService
            llm=object.__new__(FreeLLMService);llm.__init__();llm.infer_sales_json=infer
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),cache,llm)
            svc.config=MatrixConfig(stream_delay_sec=0)
            svc.freshness_repo=SimpleNamespace(get_seen_product_ids=AsyncMock(return_value=set()),mark_products_as_seen=AsyncMock())
            svc._fetch_personal=AsyncMock(return_value=[] if mode=='empty' else rows)
            svc._fetch_bestsellers=AsyncMock(return_value=[]);svc._fetch_trending=AsyncMock(return_value=[]);svc._fetch_deals=AsyncMock(return_value=[])
            if mode=='demo_preview_seen':
                from app.services.ai_nlu_service import RedisProductFreshnessRepository
                svc.freshness_repo=RedisProductFreshnessRepository(cache)
                from sqlalchemy import select
                all_ids=set((await db.execute(select(Product.id))).scalars())
                await svc.freshness_repo.mark_products_as_seen(3,all_ids)
                svc._fetch_personal=AsyncMock(return_value=[])
                svc._fetch_bestsellers=AINLUService._fetch_bestsellers.__get__(svc)
                svc._fetch_trending=AINLUService._fetch_trending.__get__(svc)
                svc._fetch_deals=AINLUService._fetch_deals.__get__(svc)
                original_pool=svc._eligible_opening_pool
                async def fixture_pool(*args,**kwargs):
                    return [p for p in await original_pool(*args,**kwargs) if p.id in ids]
                svc._eligible_opening_pool=fixture_pool
            with caplog.at_level(__import__("logging").INFO,logger="airdeliver.commerce_os"):
                await svc._handle_initial_suggestions(3)
            await asyncio.gather(*tuple(svc.tasks._tasks))
        event=await subscriber.get_message(ignore_subscribe_messages=True, timeout=1)
        if event is not None:published.append(json.loads(event["data"]))
        await subscriber.aclose()
        if mode in {'ok','demo_preview','demo_preview_seen'}:
            assert 'matrix_generation_completed' in caplog.text
            assert 'opening_pool_evaluated' in caplog.text
            assert len(published)==1 and published[0]['type']=='proactive_suggestion'
            assert published[0]['content'].endswith('Explore the current local catalog selection.')
            if mode in {'demo_preview','demo_preview_seen'}:
                assert published[0]['content'].startswith('Demo catalog preview')
                assert published[0]['products'][0]['evidence_kind']=='seeded_demo'
                assert published[0]['products'][0]['stock_status']=='demo'
                assert calls[0]['request_evidence']['demo_preview'] is True
            assert published[0]['reason'].startswith('Consider the listed material')
            assert published[0]['products'][0]['price']=='20.00'
            assert calls[0]['request_evidence']['sales_intent']=='OPENING_INSIGHT'
            assert len(calls)==(6 if mode=='demo_preview_seen' else 2)
            if mode=='demo_preview_seen':
                assert await svc.freshness_repo.get_seen_product_ids(3)==all_ids
                assert 'opening_demo_seen_replay' in caplog.text
            else:
                svc.freshness_repo.mark_products_as_seen.assert_awaited_once()
                assert svc.freshness_repo.mark_products_as_seen.await_args.kwargs["product_ids"]==set(ids)
        else:
            if mode!='price_changed':
                assert 'matrix_generation_completed' not in caplog.text
                assert published[0]['status']=='retryable'
                assert published[0]['opening_stage']==('no_eligible_cards' if mode in {'demo','empty'} else 'model_copy_unavailable')
            assert not any(p.get('products') for p in published)
            assert published and published[0]['type'] in {'info','error'}
            svc.freshness_repo.mark_products_as_seen.assert_not_awaited()
            if mode in {'demo','empty'}:assert calls==[]
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_opening_strict_publication_propagates_real_redis_outage(real_cache):
    from app.services.ai_nlu_service import UiGateway
    cache,process=real_cache
    service=object.__new__(AINLUService)
    service.ui=UiGateway(cache)
    process.terminate();await asyncio.to_thread(process.wait,3)
    with pytest.raises(Exception):
        await service._send_to_ui(3,{"type":"info","content":"test"},strict=True)
