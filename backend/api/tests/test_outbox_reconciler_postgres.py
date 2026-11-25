"""Concurrent recovered dispatch through actual PostgreSQL locks, fake transport."""
import asyncio,os
from uuid import uuid4
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import delete,select,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.user import User
from app.models.order import Order
from app.models.payment_outbox import PaymentOutbox
from app.services.payment_outbox_service import stage_payment_events
from app.services.payment_outbox_reconciler import reconcile_once,pending_summary
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')
@pytest.mark.asyncio
async def test_two_runners_restart_backoff_and_stable_ids():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);uid=oid=None
 try:
  async with sessions() as db:
   assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
   user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add(user);await db.commit();uid=user.id
   order=Order(user_id=uid,is_paid=True,total_price=10);db.add(order);await db.commit();oid=order.id
   stage_payment_events(db,order);await db.commit()
  assert await pending_summary(sessions)=={'pending':3,'due':3}
  ids=[]
  async def publish(payload,key,**kwargs):
   ids.append(kwargs['message_id']);assert kwargs['message_id']==payload['event_id'];await asyncio.sleep(.02)
   return SimpleNamespace(is_success=True)
  broker=SimpleNamespace(publish=publish)
  outcomes=await asyncio.gather(reconcile_once(sessions,broker,batch_size=2),reconcile_once(sessions,broker,batch_size=2))
  assert sum(r.sent for r in outcomes)==3 and len(ids)==len(set(ids))==3
  assert await pending_summary(sessions)=={'pending':0,'due':0}
  assert (await reconcile_once(sessions,broker)).sent==0
  # Simulate committed event recovery after a previous NACK and process loss.
  async with sessions() as db:
   row=(await db.execute(select(PaymentOutbox).where(PaymentOutbox.order_id==oid))).scalars().first()
   recovered_id=row.id;row.delivered_at=None;row.next_attempt_at=datetime.now(timezone.utc)-timedelta(seconds=1);db.add(row);await db.commit()
  failed=SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=False)))
  assert (await reconcile_once(sessions,failed,batch_size=1)).failed==1
  assert (await pending_summary(sessions))=={'pending':1,'due':0}
  assert (await reconcile_once(sessions,broker)).sent==0
  async with sessions() as db:
   row=await db.get(PaymentOutbox,recovered_id);row.next_attempt_at=datetime.now(timezone.utc)-timedelta(seconds=1);db.add(row);await db.commit()
  assert (await reconcile_once(sessions,broker)).sent==1 and ids[-1]==recovered_id
 finally:
  if uid:
   async with sessions() as db:
    await db.execute(delete(PaymentOutbox).where(PaymentOutbox.order_id==oid));await db.execute(delete(Order).where(Order.id==oid));await db.execute(delete(User).where(User.id==uid));await db.commit()
  await engine.dispose()
