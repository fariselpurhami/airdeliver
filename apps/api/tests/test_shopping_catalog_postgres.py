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
