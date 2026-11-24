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
@pytest.mark.parametrize('mode',['ok','price_changed','offline','rejected','one_paragraph','demo','empty','fixture_on','fixture_off'])
async def test_opening_model_insight_and_current_cards_through_real_publication(real_cache, mode,caplog,monkeypatch):
    if mode.startswith('fixture_'):
        from app.services import catalog_visibility
        monkeypatch.setattr(catalog_visibility,'fixtures_enabled',lambda:mode=='fixture_on')
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name='Catalog case',description='',category='accessories',price=20,inventory=10,currency='USD',attributes={'material':'cotton'})]
            if mode=='demo':rows[0].attributes={'_seed_dataset':'airdeliver-demo-v1'}
            if mode.startswith('fixture_'):rows[0].attributes={'_seed_dataset':'airdeliver-dev-fixtures-v1'}
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
            for row in rows:await db.refresh(row)
        calls=[];published=[]
        subscriber=cache.client.pubsub()
        await subscriber.subscribe(RedisKeys.ui_channel(3))
        await subscriber.get_message(timeout=1)
        async def infer(messages):
            data=json.loads(messages[1]['content']);calls.append(data)
            if mode=='offline':raise ConnectionError('controlled transport failure')
            if 'catalog_evidence' in data or 'rows' in data:
                if mode=='price_changed':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(price=30));await writer.commit()
                intro='Explore the current local catalog selection.'
                insight='Consider the listed material in the card before deciding. Merchant availability is unverified.'
                draft={'text':intro+(' ' if mode=='one_paragraph' else '\n\n')+insight,'product_ids':[],'claims':[]}
                return json.dumps({'rows':[{'row':r['row'],'draft':draft} for r in data['rows']]} if 'rows' in data else draft)
            return json.dumps(dict(supported=mode!='rejected',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        async with sessions() as db:
            from app.services.free_llm_service import FreeLLMService
            llm=object.__new__(FreeLLMService);llm.__init__();llm.infer_sales_json=infer
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),cache,llm)
            svc.config=MatrixConfig(stream_delay_sec=0)
            svc.freshness_repo=SimpleNamespace(get_seen_product_ids=AsyncMock(return_value=set()),mark_products_as_seen=AsyncMock())
            svc._fetch_personal=AsyncMock(return_value=[] if mode=='empty' else rows)
            svc._fetch_bestsellers=AsyncMock(return_value=[]);svc._fetch_trending=AsyncMock(return_value=[]);svc._fetch_deals=AsyncMock(return_value=[])
            with caplog.at_level(__import__("logging").INFO,logger="airdeliver.commerce_os"):
                await svc._handle_initial_suggestions(3)
            await asyncio.gather(*tuple(svc.tasks._tasks))
        event=await subscriber.get_message(ignore_subscribe_messages=True, timeout=1)
        if event is not None:published.append(json.loads(event["data"]))
        await subscriber.aclose()
        if mode in {'ok','fixture_on'}:
            assert 'matrix_generation_completed' in caplog.text
            assert 'opening_pool_evaluated' in caplog.text
            assert len(published)==1 and published[0]['type']=='proactive_suggestion'
            assert published[0]['content']=='Explore the current local catalog selection.'
            assert published[0]['reason'].startswith('Consider the listed material')
            assert published[0]['products'][0]['price']=='20.00'
            if mode=='fixture_on':
                assert published[0]['products'][0]['evidence_kind']=='dev_fixture'
                assert published[0]['products'][0]['stock_status']=='fixture_in_stock'
                assert 'synthetic' in published[0]['products'][0]['availability_note']
            assert calls[0]['rows'][0]['row']=='Personalized'
            assert len(calls)==2
            svc.freshness_repo.mark_products_as_seen.assert_awaited_once()
            assert svc.freshness_repo.mark_products_as_seen.await_args.kwargs["product_ids"]==set(ids)
        else:
            if mode!='price_changed':
                assert 'matrix_generation_completed' not in caplog.text
                assert published[0]['status']=='retryable'
                assert published[0]['opening_stage']==('no_eligible_cards' if mode in {'demo','empty','fixture_off'} else 'model_copy_unavailable')
            assert not any(p.get('products') for p in published)
            assert published and published[0]['type'] in {'info','error'}
            svc.freshness_repo.mark_products_as_seen.assert_not_awaited()
            if mode in {'demo','empty','fixture_off'}:assert calls==[]
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

@pytest.mark.asyncio
async def test_four_opening_copy_chains_do_not_burst_concurrently(real_cache):
    cache,_=real_cache
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    ids=[];active=peak=0
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=f'Eligible catalog item {i}',description='',category='accessories',price=20,inventory=5,currency='USD') for i in range(4)]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async with sessions() as db:
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),cache,SimpleNamespace())
            svc.config=MatrixConfig(stream_delay_sec=0)
            svc.freshness_repo=SimpleNamespace(get_seen_product_ids=AsyncMock(return_value=set()),mark_products_as_seen=AsyncMock())
            for name,row in zip(['personal','bestsellers','trending','deals'],rows):setattr(svc,'_fetch_'+name,AsyncMock(return_value=[row]))
            async def generate(*args):
                nonlocal active,peak
                active+=1;peak=max(peak,active)
                try:
                    await asyncio.sleep(.01)
                    return 'Model introduction','Model Insight'
                finally:active-=1
            svc._generate_dynamic_row_copy=generate
            svc._stream_row=AsyncMock()
            await svc._handle_initial_suggestions(3)
            await asyncio.gather(*tuple(svc.tasks._tasks))
            assert peak==1 and svc._stream_row.await_count==4
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()

@pytest.mark.asyncio
@pytest.mark.parametrize('empty_role',[None,'Bestsellers'])
async def test_original_four_role_stack_order_no_crossrole_backfill(real_cache,empty_role):
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    roles=['Personalized','Bestsellers','Trending','Deals'];published=[];written=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=role+' real catalog item',description='',category=role,price=20,inventory=3,currency='USD') for role in roles]
            db.add_all(rows);await db.commit();ids=[row.id for row in rows]
            for row in rows:await db.refresh(row)
        async def infer(messages):
            data=json.loads(messages[1]['content'])
            if 'catalog_evidence' in data or 'rows' in data:
                draft={'text':'Explore this local catalog section.\n\nVerify the listed details and merchant availability before choosing.','product_ids':[],'claims':[]}
                if 'rows' in data:
                    written.extend(r['row'] for r in data['rows'])
                    return json.dumps({'rows':[{'row':r['row'],'draft':draft} for r in data['rows']]})
                role=data['request_evidence']['row_pool'];written.append(role)
                return json.dumps(draft)
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        async with sessions() as db:
            from app.services.free_llm_service import FreeLLMService
            llm=object.__new__(FreeLLMService);llm.__init__();llm.infer_sales_json=infer
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),cache,llm)
            svc.config=MatrixConfig(stream_delay_sec=0)
            async def publish(channel,message):published.append(json.loads(message));return 1
            cache.publish_required=publish
            svc.freshness_repo=SimpleNamespace(get_recent_product_ids=AsyncMock(return_value=set()),mark_products_as_seen=AsyncMock())
            for method,row,role in zip(['_fetch_personal','_fetch_bestsellers','_fetch_trending','_fetch_deals'],rows,roles):
                setattr(svc,method,AsyncMock(return_value=[] if role==empty_role else [row]))
            await svc._handle_initial_suggestions(3)
            if svc.tasks._tasks:await asyncio.gather(*tuple(svc.tasks._tasks))
        expected=[role for role in roles if role!=empty_role]
        assert written==expected
        assert [event['products'][0]['name'] for event in published]==[role+' real catalog item' for role in expected]
        assert [event['type'] for event in published]==['proactive_suggestion']+['product_carousel']*(len(expected)-1)
        assert len(published)==(4 if empty_role is None else 3)
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
