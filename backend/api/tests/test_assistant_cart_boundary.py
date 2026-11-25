"""Real migrated PostgreSQL+Redis+HTTP, fixture inference, no LLM/provider."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlmodel import select
from app.models.user import User
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,RouterDecision
from app.services.ai_cart_service import AICartService
from app.api.v1.endpoints import ai_ordering
from app.api import deps
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_review_does_not_write_then_explicit_http_add_remove_updates_actual_cart(real_cache):
 cache,_=real_cache
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
  user=User(email=uuid4().hex+'@example.test',hashed_password='fixture')
  product=Product(sku=uuid4().hex,name='Exact Boundary Headphones',description='',price='25.00',inventory=10)
  db.add_all([user,product]);await db.commit();uid,pid=user.id,product.id
 class Search:
  async def perform_hybrid_search_pure(self,db,query,limit):
   return (await db.execute(select(Product).where(Product.id==pid))).scalars().all()
 service=NeuralCoreService(Search(),cache)
 service._analyze_intent=AsyncMock(return_value=RouterDecision(intent='CART_ADD',query=product.name,quantity=2))
 async with sessions() as db:
  response=await service.handle_message(db,'add2 Exact Boundary Headphones',user,'fixture-session')
 assert response.action.payload.product_id==pid
 assert await cache.get_json_required(f'ai_cart:{uid}') is None
 app=FastAPI();app.include_router(ai_ordering.router)
 async def dbdep():
  async with sessions() as db:yield db
 async def cartdep():
  async with sessions() as db:yield AICartService(db,cache,SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True))))
 app.dependency_overrides[deps.get_current_active_user]=lambda:user
 app.dependency_overrides[deps.get_async_session]=dbdep
 app.dependency_overrides[ai_ordering.get_ai_cart_service]=cartdep
 try:
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
   key=str(uuid4());body={'product_id':pid,'quantity':2}
   for _ in range(2):
    assert (await client.post('/cart/add',json=body,headers={'Idempotency-Key':key})).status_code==202
   cart=(await client.get('/cart')).json();assert cart['items'][0]['quantity']==2
   assert cart['items'][0]['product_id']==pid
   assert (await client.post('/cart/remove',json={'product_id':pid},headers={'Idempotency-Key':str(uuid4())})).status_code==202
   assert (await client.get('/cart')).json()['items']==[]
 finally:await engine.dispose()
