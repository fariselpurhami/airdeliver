import asyncio
import os
from uuid import uuid4
import pytest
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from sqlalchemy import text,func
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlmodel import select
from app.api import deps
from app.api.v1.endpoints.admin import router
from app.models.user import User
from app.models.order import Order
from app.models.audit_trail import AuditTrail
from app.models.notification import Notification
from app.models.enums import OrderStatus
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_manual_fulfillment_permissions_transitions_audit_notification_and_replay():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
  admin=User(email=uuid4().hex+'@example.test',hashed_password='fixture',role='admin')
  owner=User(email=uuid4().hex+'@example.test',hashed_password='fixture')
  db.add_all([admin,owner]);await db.commit()
  paid=Order(user_id=owner.id,status=OrderStatus.PROCESSING,is_paid=True);unpaid=Order(user_id=owner.id)
  db.add_all([paid,unpaid]);await db.commit();oid,unpaid_id=paid.id,unpaid.id
 app=FastAPI();app.include_router(router)
 async def dbdep():
  async with sessions() as db:yield db
 actor=[owner];app.dependency_overrides[deps.get_async_session]=dbdep
 app.dependency_overrides[deps.get_current_active_user]=lambda:actor[0]
 payload={'from_status':'processing','to_status':'assigned','evidence':'Assigned to warehouse operator fixture'}
 try:
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
   assert (await client.post(f'/orders/{oid}/fulfillment',json=payload)).status_code==403
   actor[0]=admin
   listed=await client.get('/orders');assert listed.status_code==200 and listed.json()['total_orders']>=2
   assert (await client.post(f'/orders/{unpaid_id}/fulfillment',json=payload)).status_code==409
   assert (await client.post(f'/orders/{oid}/fulfillment',json={**payload,'to_status':'delivered'})).status_code==409
   assert (await client.post(f'/orders/{oid}/fulfillment',json={**payload,'evidence':'x'})).status_code==422
   results=await asyncio.gather(*(client.post(f'/orders/{oid}/fulfillment',json=payload) for _ in range(2)))
   assert all(r.status_code==200 for r in results)
   assert sorted(r.json()['replayed'] for r in results)==[False,True]
   assert (await client.post(f'/orders/{oid}/fulfillment',json={**payload,'evidence':'Different stale attestation'})).status_code==409
   for before,after in [('assigned','in_transit'),('in_transit','delivered')]:
    r=await client.post(f'/orders/{oid}/fulfillment',json={'from_status':before,'to_status':after,'evidence':'Verified physical operator event fixture'})
    assert r.status_code==200 and r.json()['source']=='manual_operator'
  async with sessions() as db:
   stored=await db.get(Order,oid);assert stored.is_paid and stored.status==OrderStatus.DELIVERED
   events=(await db.execute(select(AuditTrail).where(AuditTrail.order_id==oid))).scalars().all()
   notices=(await db.execute(select(Notification).where(Notification.related_order_id==oid))).scalars().all()
   assert len(events)==len(notices)==3
   assert all(e.changed_by==admin.id for e in events)
   assert all(n.user_id==owner.id and n.meta['source']=='manual_operator' and n.meta['cta']==f'/tracking/{oid}' for n in notices)
 finally:await engine.dispose()
