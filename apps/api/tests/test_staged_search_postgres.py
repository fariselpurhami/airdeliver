"""Staged target search through mounted HTTP, real SQL and Redis history.
Retrieval and model transport controlled at their actual boundaries. No provider.
"""
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,update,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,get_neural_core_service
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','changed','target_timeout','missing'])
@pytest.mark.parametrize('task',['comparison','specifications','consultation'])
async def test_multi_target_http_actual_sql_history_and_fresh_publication(real_cache,mode,task):
    cache,_=real_cache
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name=name,description='',category='audio',price=20,inventory=5,currency='USD',attributes={'connection':value}) for name,value in [('Alpha headphones','wired'),('Beta headphones','Bluetooth')]]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async def retrieve(db,query,**kwargs):
            if query=='Beta headphones' and mode=='target_timeout':raise TimeoutError('controlled target timeout')
            if query=='Beta headphones' and mode=='missing':return []
            result=await db.execute(__import__('sqlalchemy').select(Product).where(Product.name==query))
            return result.scalars().all()
        search=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve))
        svc=NeuralCoreService(search,cache);svc.is_healthy=True;svc.configuration_error=False
        requests=[]
        async def infer(messages):
            if 'primary cognitive routing' in messages[0]['content']:
                return json.dumps(dict(intent='PRODUCT_SEARCH',query='Alpha headphones',search_subject='Alpha headphones',shopping_task=task,targets=[{'product_name':n} for n in ['Alpha headphones','Beta headphones']]))
            payload=json.loads(messages[1]['content']);requests.append(payload)
            if 'catalog_evidence' in payload:
                if mode=='changed':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(price=30));await writer.commit()
                return json.dumps(dict(text='Compare the listed connection details in the cards. Unknown specifications and merchant availability need verification.',product_ids=[],claims=[]))
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=infer
        from httpx import AsyncClient,ASGITransport
        from app.main import app
        from app.db.session import get_async_session
        from app.services.cache_service import get_cache_from_request
        async def get_db():
            async with sessions() as db:yield db
        app.dependency_overrides[get_async_session]=get_db
        app.dependency_overrides[get_neural_core_service]=lambda:svc
        app.dependency_overrides[get_cache_from_request]=lambda:cache
        try:
            async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post('/api/v1/ai-support/chat',json={'message':'Compare Alpha headphones and Beta headphones','session_id':'staged-test-session'})
            assert response.status_code==200,response.text
            data=response.json()
            if mode in {'changed','target_timeout'}:
                assert data['response_kind']=='system_notice' and data['products']==[]
            else:
                assert [p['id'] for p in data['products']]==ids[:1 if mode=='missing' else 2]
                evidence=requests[0]['request_evidence']
                assert evidence['shopping_task']==task
                assert evidence['sales_intent']=='CATALOG_CONSULTATION'
                assert [t['target'] for t in evidence['target_searches']]==['Alpha headphones','Beta headphones']
                assert evidence['missing_target_evidence_is_unknown'] is True
                if mode=='missing':assert evidence['target_searches'][1]['tier']=='no_match'
            history=await cache.get_json_required(svc._get_session_key('staged-test-session'))
            assert history['history'][-1]['content']==data['text']
            assert all(call.args[1] in {'Alpha headphones','Beta headphones'} for call in search.perform_hybrid_search_pure.call_args_list)
        finally:app.dependency_overrides.clear()
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()

@pytest.mark.asyncio
@pytest.mark.parametrize('task',['specifications','comparison','consultation'])
@pytest.mark.parametrize('with_targets',[True,False])
async def test_product_research_http_no_catalog_stock_requirement(real_cache,monkeypatch,task,with_targets):
    from app.services import product_knowledge_service as knowledge
    from httpx import AsyncClient,ASGITransport
    from app.main import app
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    cache,_=real_cache
    async def sources(q):return [{'url':'https://maker.example/phone-specs','text':'Phone 17 Pro Max has an OLED display.'}]
    monkeypatch.setattr(knowledge,'lookup_product_sources',sources)
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    search=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=AssertionError('research must not require catalog')))
    svc=NeuralCoreService(search,cache);svc.is_healthy=True;svc.configuration_error=False
    async def infer(messages):
        if 'primary cognitive routing' in messages[0]['content']:
            return json.dumps(dict(intent='PRODUCT_SEARCH',query='Phone 17 Pro Max',search_subject='Phone 17 Pro Max',shopping_task=task,targets=[{'product_name':'Phone 17 Pro Max'}] if with_targets else []))
        if 'Extract source-backed' in messages[0]['content']:
            return json.dumps({'covered_targets':['Phone 17 Pro Max'],'facts':[{'label':'Display','statement':'The source lists an OLED display.','quote':'Phone 17 Pro Max has an OLED display.','source':0}]})
        return json.dumps({'supported':True,'exact_model':True,'product_information_only':True})
    svc._execute_llm_inference=infer
    async def get_db():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=get_db
    app.dependency_overrides[get_neural_core_service]=lambda:svc
    app.dependency_overrides[get_cache_from_request]=lambda:cache
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/ai-support/chat',json={'message':'Phone 17 Pro Max specs','session_id':'web-research-session'})
        assert response.status_code==200,response.text
        data=response.json()
        assert data['response_kind']=='text' and 'OLED' in data['text'] and 'https://maker.example/phone-specs' in data['text']
        assert data['products']==[]
        search.perform_hybrid_search_pure.assert_not_awaited()
        history=await cache.get_json_required(svc._get_session_key('web-research-session'))
        assert history['history'][-1]['content']==data['text']
    finally:
        app.dependency_overrides.clear();await engine.dispose()

@pytest.mark.asyncio
async def test_setup_http_plans_components_and_publishes_real_current_cards(real_cache):
    from httpx import AsyncClient,ASGITransport
    from app.main import app
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    cache,_=real_cache;engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=name,description='',category='office',price=20,inventory=5,currency='USD') for name in ['Office desk','Office chair']]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async def retrieve(db,query,**kwargs):
            result=await db.execute(select(Product).where(Product.id.in_(ids),Product.name.ilike('%'+query+'%')))
            return result.scalars().all()
        from sqlalchemy import select
        svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve)),cache);svc.is_healthy=True;svc.configuration_error=False
        async def infer(messages):
            prompt=messages[0]['content']
            if 'primary cognitive routing' in prompt:return json.dumps({'intent':'SETUP_DISCOVERY','search_subject':'home office setup'})
            if 'Plan generic component' in prompt:return json.dumps({'components':['desk','chair']})
            if 'Review a generic setup' in prompt:return json.dumps({'appropriate':True,'no_invented_products':True})
            data=json.loads(messages[1]['content'])
            if 'catalog_evidence' in data:
                assert data['request_evidence']['shopping_task']=='setup'
                return json.dumps({'text':'These cards are possible components. Compatibility and a complete setup have not been verified.','product_ids':[],'claims':[]})
            return json.dumps({'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True})
        svc._execute_llm_inference=infer
        async def get_db():
            async with sessions() as db:yield db
        app.dependency_overrides[get_async_session]=get_db
        app.dependency_overrides[get_neural_core_service]=lambda:svc
        app.dependency_overrides[get_cache_from_request]=lambda:cache
        try:
            async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
                response=await client.post('/api/v1/ai-support/chat',json={'message':'build a home office setup','session_id':'setup-real-test'})
            assert response.status_code==200,response.text
            assert [p['id'] for p in response.json()['products']]==ids
            assert 'Compatibility' in response.json()['text']
        finally:app.dependency_overrides.clear()
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()

@pytest.mark.asyncio
async def test_http_hard_features_use_fresh_sql_lexical_evidence_not_substrings(real_cache):
    from httpx import AsyncClient,ASGITransport
    from app.main import app
    from app.db.session import get_async_session
    from app.services.cache_service import get_cache_from_request
    cache,_=real_cache
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=name,description='',category='computers',price=20,inventory=5,currency='USD',attributes={'memory':ram}) for name,ram in [('Infrared laptop','16 GB RAM'),('Other laptop','116GB RAM'),('Red laptop','16GB RAM')]]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async def retrieve(db,query,**kw):
            return (await db.execute(__import__('sqlalchemy').select(Product).where(Product.id.in_(ids)))).scalars().all()
        svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=retrieve),cache);svc.is_healthy=True;svc.configuration_error=False
        async def infer(messages):
            if 'primary cognitive routing' in messages[0]['content']:
                return json.dumps({'intent':'PRODUCT_SEARCH','query':'laptop','search_subject':'laptop','brief':{'required_features':['16GB RAM'],'excluded_terms':['red']}})
            payload=json.loads(messages[1]['content'])
            if 'catalog_evidence' in payload:return json.dumps({'text':'Review the listed facts in these cards.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=infer
        async def get_db():
            async with sessions() as db:yield db
        app.dependency_overrides[get_async_session]=get_db
        app.dependency_overrides[get_neural_core_service]=lambda:svc
        app.dependency_overrides[get_cache_from_request]=lambda:cache
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            r=await client.post('/api/v1/ai-support/chat',json={'message':'laptop with16GB RAM, no red','session_id':'features-real-boundary'})
        assert r.status_code==200,r.text
        assert [p['id'] for p in r.json()['products']]==ids[:1]
    finally:
        app.dependency_overrides.clear()
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
