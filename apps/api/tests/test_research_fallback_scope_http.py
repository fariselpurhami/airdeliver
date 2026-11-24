"""Retained target constraints survive advisory task changes at mounted HTTP."""
import json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,SessionMemory,get_neural_core_service
from app.services.shopping_discovery import ShoppingBrief
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')

@pytest.mark.asyncio
@pytest.mark.parametrize('task',['comparison','specifications','consultation'])
@pytest.mark.parametrize('mode',['ok','wrong_ram','changed','identity_change','source_success'])
async def test_research_catalog_fallback_retains_scope_after_empty_sources(real_cache,monkeypatch,task,mode):
    from app.services import product_knowledge_service
    lookup=AsyncMock(return_value=[{'url':'https://maker.example/specs','text':'Atlas laptop has a wired connection.'}] if mode=='source_success' else [])
    monkeypatch.setattr(product_knowledge_service,'lookup_product_sources',lookup)
    cache,_=real_cache;native=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(native,expire_on_commit=False);ids=[];seen=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name='Atlas laptop',description='',category='computers',price=20,inventory=3,currency='USD',attributes={'RAM':'8GB' if mode=='wrong_ram' else '32GB'}),Product(sku=uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,inventory=3,currency='USD',attributes={'color':'blue'})]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        async def retrieve(db,query,**kw):
            result=await db.execute(select(Product).where(Product.id.in_(ids),Product.name==query))
            return result.scalars().all()
        svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve)),cache);svc.is_healthy=True;svc.configuration_error=False
        memory=SessionMemory(user_name='test',shopping_brief=ShoppingBrief(required_features=['at least 16GB RAM'],excluded_terms=['red']),target_requirements={'Atlas laptop':['at least 16GB RAM']},target_exclusions={'Atlas chair':['red']})
        memory.append_turn('Atlas laptop at least 16GB RAM and Atlas chair without red','Previous scoped selection.')
        await cache.set_json_required(svc._get_session_key('advisory-scope'),memory.model_dump(),ttl=600)
        names=['Notebook' if mode=='identity_change' else 'Atlas laptop','Atlas chair']
        async def infer(messages):
            policy=messages[0]['content']
            if 'primary cognitive routing' in policy:
                return json.dumps(dict(intent='PRODUCT_SEARCH',query=names[0],search_subject=names[0],shopping_task=task,targets=[{'product_name':n} for n in names]))
            data=json.loads(messages[1]['content'])
            if 'Extract source-backed' in policy:
                return json.dumps({'covered_targets':names,'facts':[{'label':'Connection','quote':'Atlas laptop has a wired connection.','source':0}]})
            if 'untrusted_sources' in data.get('input',data) or 'product_information_only' in policy:
                return json.dumps({'supported':True,'exact_model':True,'product_information_only':True})
            if 'Assign existing hard features' in policy:return '{"assignments":[]}'
            if 'Review exact target/feature scope' in policy:return '{"explicit_scope":true}'
            if 'catalog_evidence' in data:
                seen.append(data)
                if mode=='changed':
                    async with sessions() as db:
                        await db.execute(update(Product).where(Product.id==ids[0]).values(attributes={'RAM':'8GB'}));await db.commit()
                return json.dumps(dict(text='The cards show current catalog details. Discounts and suitability remain unverified.',product_ids=[],claims=[]))
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
                response=await client.post('/api/v1/ai-support/chat',json={'message':task+' for '+names[0]+' and Atlas chair','session_id':'advisory-scope'})
            assert response.status_code==200,response.text
            result=response.json()
            if mode=='source_success':
                assert result['response_kind']=='text' and result['products']==[]
                assert 'wired connection' in result['text']
                svc.ai_engine.perform_hybrid_search_pure.assert_not_awaited()
            elif mode=='identity_change':
                assert result['response_kind']=='clarification' and result['products']==[] and not seen
                svc.ai_engine.perform_hybrid_search_pure.assert_not_awaited()
            elif mode=='changed':assert result['response_kind']=='system_notice' and result['products']==[]
            else:
                assert [p['id'] for p in result['products']]==(ids[1:] if mode=='wrong_ram' else ids)
                context=seen[0]['request_evidence']
                assert context['shopping_task']==task
                assert context['target_searches'][0]['required_features']==['at least 16GB RAM']
                assert context['target_searches'][1]['excluded_terms']==['red']
            stored=await cache.get_json_required(svc._get_session_key('advisory-scope'))
            assert stored['target_requirements']==memory.target_requirements
            assert stored['target_exclusions']==memory.target_exclusions
        finally:app.dependency_overrides.clear()
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await native.dispose()
