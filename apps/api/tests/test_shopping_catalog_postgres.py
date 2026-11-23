"""Current-row and full HTTP contract against migrated disposable PostgreSQL.
Only retrieval ordering and model transport are controlled at their boundaries."""
import os,json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,update,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService
from app.services.shopping_discovery import ShoppingBrief

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires migrated disposable PostgreSQL')

@pytest.mark.asyncio
async def test_current_cards_survive_http_but_stale_inactive_deleted_candidates_do_not(capsys):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
    ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=uuid4().hex,name='Gift option '+str(i),description='',category='accessories',price=10,currency='EUR',inventory=20) for i in range(3)]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        async with sessions() as db:
            await db.execute(update(Product).where(Product.id==ids[0]).values(name='Current catalog bag',price=Decimal('28.50'),inventory=0,
                attributes={'_seed_dataset':'airdeliver-demo-v1'}))
            await db.execute(update(Product).where(Product.id==ids[1]).values(is_active=False))
            await db.execute(delete(Product).where(Product.id==ids[2]));await db.commit()
        svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=rows+rows)),object());svc.is_healthy=True
        draft=dict(text='Compare the demo catalog card below. Its price and stock are synthetic, not a merchant offer.',product_ids=[],claims=[])
        svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(draft),json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
        async with sessions() as db:
            response=await svc._handle_product_search(db,'bags')
        assert len(response.products)==1
        card=response.products[0]
        assert (card.id,card.name,card.price,card.currency,card.stock_status)==(ids[0],'Current catalog bag','28.50','EUR','demo')
        assert card.evidence_kind=='seeded_demo'
        assert response.text==draft['text']
        from scripts.inspect_catalog_product import inspect
        await inspect('Current catalog bag',engine)
        output=json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert len(output['rows'])==1 and output['rows'][0]['seed_dataset']=='airdeliver-demo-v1'
        assert set(output['rows'][0])=={'id','sku','name','price','currency','inventory','is_active','seed_dataset','updated_at'}
        # Real mounted route/response serialization, not a substitute DTO route.
        from httpx import AsyncClient,ASGITransport
        from app.main import app
        from app.api import deps
        from app.services.neural_core_service import get_neural_core_service
        from app.services.cache_service import get_cache_from_request
        svc._hydrate_session=AsyncMock(return_value=__import__('app.services.neural_core_service',fromlist=['SessionMemory']).SessionMemory(user_name='Client'))
        svc._persist_session=AsyncMock()
        svc._analyze_intent=AsyncMock(return_value=__import__('app.services.neural_core_service',fromlist=['RouterDecision']).RouterDecision(intent='PRODUCT_SEARCH',query='bags',search_subject='bags'))
        svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(draft),json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
        async def get_db():
            async with sessions() as db:yield db
        from app.db.session import get_async_session
        app.dependency_overrides[get_async_session]=get_db
        app.dependency_overrides[get_neural_core_service]=lambda:svc
        app.dependency_overrides[get_cache_from_request]=lambda:SimpleNamespace(incr=AsyncMock(return_value=1),expire=AsyncMock())
        try:
            async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
                resp=await client.post('/api/v1/ai-support/chat',json={'message':'bags','session_id':'test-evidence'})
            assert resp.status_code==200,resp.text
            assert resp.json()['products'][0]['id']==ids[0]
            assert resp.json()['products'][0]['currency']=='EUR'
            assert resp.json()['text']==draft['text']
        finally:app.dependency_overrides.clear()
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_unavailable_requested_item_pivots_only_to_current_non_demo_positive_stock():
    from app.services.neural_core_service import RouterDecision
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=name,description='',category='smartwatches',price=price,currency='USD',inventory=qty,attributes=attrs)
                for name,price,qty,attrs in [('Apple Watch',200,0,{}),('Trail Smartwatch',80,7,{'battery':'48 hours'}),
                    ('Demo Watch',50,80,{'_seed_dataset':'airdeliver-demo-v1'}),('Empty Watch',40,0,{}),('Too costly Watch',500,5,{})]]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        api=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=[[rows[0]],rows[1:]]),
            find_genius_alternatives=AsyncMock(return_value=rows[1:]))
        svc=NeuralCoreService(api,object());svc.is_healthy=True
        draft=dict(text='Apple Watch has no stock in the current catalog results. Trail Smartwatch is a lower-priced local catalog option, with battery listed as48 hours. Merchant stock is not verified.',
            product_ids=[ids[1]],claims=[{'product_id':ids[1],'field':'name','value':'Trail Smartwatch'},
                {'product_id':ids[1],'field':'spec.battery','value':'48 hours'}])
        verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(draft),verdict])
        brief=ShoppingBrief(budget='under USD100',budget_max='100',budget_currency='USD')
        async with sessions() as db:
            result=await svc._handle_product_search(db,'Apple Watch',brief,'Apple Watch for my wife under USD100',
                RouterDecision(intent='PRODUCT_SEARCH',query='Apple Watch',search_subject='Apple Watch',requested_name='Apple Watch',alternative_query='smartwatch'))
        assert result.response_kind=='catalog_results'
        assert [c.id for c in result.products]==[ids[1]]
        assert result.products[0].relation=='alternative' and result.products[0].catalog_specs=={'battery':'48 hours'}
        assert api.find_genius_alternatives.await_count==1
        writer_payload=json.loads(svc._execute_llm_inference.call_args_list[0].args[0][1]['content'])
        assert writer_payload['request_evidence']['unavailable_requested'][0]['stock_status']=='local_out_of_stock'
        # A missing named item (no anchor) still gets bounded functional retrieval.
        api.perform_hybrid_search_pure=AsyncMock(side_effect=[[],[rows[1],rows[2]]])
        svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(draft),verdict])
        async with sessions() as db:
            result=await svc._handle_product_search(db,'Apple Watch',brief,'Apple Watch for my wife under USD100',
                RouterDecision(intent='PRODUCT_SEARCH',requested_name='Apple Watch',alternative_query='smartwatch'))
        assert [c.id for c in result.products]==[ids[1]]
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_owner_jewelry_dollar_followup_keeps_budget_and_eligible_card():
    from app.services.neural_core_service import SessionMemory
    from tests.test_neural_session_isolation import Cache
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name=name,description='',category='jewelry',price=price,currency='USD',inventory=qty)
                  for name,price,qty in [('Silver pendant',100,4),('Over cap necklace',1500,3),('Empty pendant',50,0)]]
            db.add_all(rows);await db.commit();ids=[p.id for p in rows]
        cache=Cache();svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=rows)),cache)
        svc.is_healthy=True;svc.configuration_error=False
        initial=SessionMemory(user_name='Client',history=[{'role':'user','content':'I want a gift for my wife'},{'role':'assistant','content':'What occasion, interests and budget?'}])
        await cache.set_json(svc._get_session_key('owner-gift-regression'),initial.model_dump(mode='json'))
        router={'intent':'PRODUCT_SEARCH','query':'jewelry','search_subject':'jewelry','brief':{'category':'jewelry','occasion':'birthday','budget':'1000 dollar','budget_max':'1000','budget_currency':'USD'}}
        draft={'text':'Within your 1000 dollar budget, compare Silver pendant in the card. Local catalog stock is listed, merchant availability is unverified.', 'product_ids':[ids[0]],'claims':[{'product_id':ids[0],'field':'name','value':'Silver pendant'}]}
        verdict=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
        svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(router),json.dumps(draft),json.dumps(verdict)])
        async with sessions() as db:
            result=await svc.handle_message(db,'Her birthday, and I want jewelry and the budget at range 1000 dollar',None,'owner-gift-regression')
        assert result.response_kind=='catalog_results' and result.text==draft['text']
        assert [p.id for p in result.products]==[ids[0]]
        stored=cache.data[svc._get_session_key('owner-gift-regression')]
        assert stored['shopping_brief']['budget_max']=='1000'
        assert stored['shopping_brief']['budget_currency']=='USD'
    finally:
        async with sessions() as db:
            await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
