"""Mounted chat, real SQL/Redis, controlled writer/reviewer, no external providers."""
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,get_neural_core_service
from tests.test_cart_persistence_outcomes import real_cache

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')


@pytest.mark.asyncio
@pytest.mark.parametrize('rejected_field',[None,'supported','all_product_mentions_declared','no_unsupported_commercial_claims','fulfills_discovery_task'])
async def test_mounted_shared_adaptive_answer_runs_full_review_before_publish(real_cache,rejected_field):
 cache,_=real_cache
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN'])
 sessions=async_sessionmaker(engine,expire_on_commit=False);identity=None;writer=[];reviews=[]
 try:
  async with sessions() as db:
   product=Product(sku='adaptive-'+uuid4().hex,name='Synthetic Atlas laptop',description='Synthetic integration candidate, not an offer.',category='computers',price=20,inventory=3,currency='USD',attributes={'material':'canvas','evidence_kind':'dev_fixture'})
   db.add(product);await db.commit();identity=product.id
  async def retrieve(db,query,**kwargs):
   result=await db.execute(select(Product).where(Product.id==identity));return result.scalars().all()
  svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve)),cache)
  svc.is_healthy=True;svc.configuration_error=False
  async def infer(messages):
   policy=messages[0]['content']
   if 'primary cognitive routing' in policy:
    return json.dumps({'intent':'PRODUCT_SEARCH','query':'Synthetic Atlas laptop','search_subject':'Synthetic Atlas laptop','shopping_task':'search','targets':[{'product_name':'Synthetic Atlas laptop'}]})
   data=json.loads(messages[1]['content'])
   if 'catalog_evidence' in data:
    writer.append(messages)
    return json.dumps({'text':'This is a synthetic test candidate, not an offer. Water resistance is not listed, so confirm that before choosing.','product_ids':[],'claims':[]})
   if 'draft' in data and 'input' in data:
    reviews.append(messages)
    verdict=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
    if rejected_field:verdict[rejected_field]=False
    return json.dumps(verdict)
   raise AssertionError('unexpected model stage')
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
    response=await client.post('/api/v1/ai-support/chat',json={'message':'Find Synthetic Atlas laptop for rain; do not invent water resistance.','session_id':'adaptive-'+uuid4().hex})
   assert response.status_code==200,response.text
   result=response.json();assert len(writer)==len(reviews)==1
   data=json.loads(writer[0][1]['content'])
   assert data['request_evidence']['product_answer_shape']=='adaptive'
   assert 'Do not force four sections' in writer[0][0]['content']
   assert 'Reject repetitive filler' in reviews[0][0]['content']
   if rejected_field:
    assert result['response_kind']=='system_notice' and result['products']==[]
    assert 'Water resistance is not listed' not in result['text']
   else:
    assert result['response_kind']=='catalog_results'
    assert [row['id'] for row in result['products']]==[identity]
    assert 'synthetic test candidate' in result['text']
  finally:app.dependency_overrides.clear()
 finally:
  async with sessions() as db:
   if identity is not None:await db.execute(delete(Product).where(Product.id==identity));await db.commit()
  await engine.dispose()
