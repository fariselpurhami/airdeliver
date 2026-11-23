"""Real HTTP+PostgreSQL: owned detail lookup is independent of history pagination."""
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.api import deps
from app.api.v1.endpoints.orders import router
from app.models.user import User
from app.models.order import Order,OrderItem
from app.models.product import Product
from app.models.enums import OrderStatus

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable migrated PostgreSQL required')

@pytest.mark.asyncio
async def test_owned_order_detail_survives_history_cutoff_and_hides_other_owners():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
  owner=User(email=uuid4().hex+'@example.test',hashed_password='fixture')
  other=User(email=uuid4().hex+'@example.test',hashed_password='fixture')
  product=Product(sku=uuid4().hex,name='Fixture headphones',description='',price='12.50',inventory=200)
  db.add_all([owner,other,product]);await db.commit()
  old=Order(user_id=owner.id,status=OrderStatus.DELIVERED,total_price=25,currency='CAD',created_at=datetime.now(timezone.utc)-timedelta(days=365),shipping_address_data={'line1':'not-for-output'},payment_transaction_id='private-fixture')
  hidden=Order(user_id=other.id,total_price=17,currency='USD')
  db.add_all([old,hidden]);await db.commit()
  db.add(OrderItem(order_id=old.id,product_id=product.id,quantity=2,price_per_unit=12.50))
  db.add_all([Order(user_id=owner.id,total_price=1,currency='USD') for _ in range(101)])
  await db.commit();old_id,hidden_id=old.id,hidden.id
 app=FastAPI();app.include_router(router)
 async def dbdep():
  async with sessions() as db:yield db
 app.dependency_overrides[deps.get_async_session]=dbdep
 app.dependency_overrides[deps.get_current_active_user]=lambda:owner
 try:
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
   history=await client.get('/me?limit=100')
   assert history.status_code==200 and history.json()['total']==102
   assert old_id not in [row['id'] for row in history.json()['orders']]
   assert history.headers['cache-control']=='no-store'
   detail=await client.get(f'/me/{old_id}')
   assert detail.status_code==200 and detail.headers['cache-control']=='no-store'
   data=detail.json();assert data['id']==old_id and data['currency']=='CAD' and data['total_price']==25
   assert data['items'][0]['product']['name']=='Fixture headphones'
   assert not {'shipping_address_data','payment_transaction_id','checkout_data'} & data.keys()
   stranger=await client.get(f'/me/{hidden_id}')
   missing=await client.get('/me/2147483647')
   assert stranger.status_code==missing.status_code==404 and stranger.json()==missing.json()
   for value in ['0','-1','abc','2147483648']:
    assert (await client.get('/me/'+value)).status_code==422
 finally:await engine.dispose()
