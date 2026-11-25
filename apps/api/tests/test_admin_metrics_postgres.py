"""Complete currency/time/payment truth through real PostgreSQL and admin HTTP."""
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from sqlalchemy import delete,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from app.api.v1.endpoints.admin import router
from app.api import deps
from app.models.user import User
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.admin_metrics import payment_metrics
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_complete_currency_aware_paid_timestamp_window_and_permissions():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 now=datetime.now(timezone.utc);user_id=None
 try:
  async with sessions() as db:
   assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
   user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add(user);await db.commit();user_id=user.id
   orders=[Order(user_id=user_id,total_price=.1,currency='USD',is_paid=True,paid_at=now-timedelta(minutes=5),status=OrderStatus.PROCESSING) for _ in range(151)]
   orders += [Order(user_id=user_id,total_price=.2,currency='EUR',is_paid=True,paid_at=now-timedelta(hours=2)),
     Order(user_id=user_id,total_price=900,currency='USD',is_paid=False,status=OrderStatus.DELIVERED),
     Order(user_id=user_id,total_price=800,currency='USD',is_paid=True,paid_at=None),
     Order(user_id=user_id,total_price=700,currency='USD',is_paid=True,paid_at=now-timedelta(days=2)),
     Order(user_id=user_id,total_price=600,currency='USD',is_paid=True,paid_at=now+timedelta(hours=1)),
     Order(user_id=user_id,total_price=500,currency='???',is_paid=True,paid_at=now-timedelta(minutes=3)),
     Order(user_id=user_id,total_price=float('nan'),currency='USD',is_paid=True,paid_at=now-timedelta(minutes=3)),
     Order(user_id=user_id,total_price=-1,currency='USD',is_paid=True,paid_at=now-timedelta(minutes=3)),
     Order(user_id=user_id,total_price=float('inf'),currency='USD',is_paid=True,paid_at=now-timedelta(minutes=3))]
   db.add_all(orders);await db.commit()
   metrics=await payment_metrics(db,'24H',now=now)
   by={c.currency:c for c in metrics.currencies}
   assert by['USD'].amount=='15.10' and by['USD'].order_count==151
   assert by['EUR'].amount=='0.20' and by['EUR'].order_count==1
   assert metrics.paid_without_timestamp>=1 and metrics.paid_invalid_amount_or_currency==4
   assert metrics.complete and metrics.definition=='recorded_paid_order_gross'
   assert all(b.starts_at.tzinfo for c in metrics.currencies for b in c.buckets)
   # A different DB timezone cannot move paid events into another day/hour.
   await db.execute(text("SET LOCAL TIME ZONE 'Pacific/Honolulu'"))
   shifted=await payment_metrics(db,'24H',now=now)
   assert shifted.model_dump()==metrics.model_dump()
  app=FastAPI();app.include_router(router);actor=[user]
  async def dbdep():
   async with sessions() as db:yield db
  app.dependency_overrides[deps.get_async_session]=dbdep
  app.dependency_overrides[deps.get_current_active_user]=lambda:actor[0]
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
   assert (await client.get('/payment-metrics')).status_code==403
   user.role='admin'
   r=await client.get('/payment-metrics?range=24H')
   assert r.status_code==200 and r.headers['cache-control']=='no-store'
   assert r.json()['timezone']=='UTC' and len(r.json()['currencies'])==2
   assert (await client.get('/payment-metrics?range=all')).status_code==422
 finally:
  if user_id:
   async with sessions() as db:
    await db.execute(delete(Order).where(Order.user_id==user_id));await db.execute(delete(User).where(User.id==user_id));await db.commit()
  await engine.dispose()
