"""Independent real DB sessions prove cancellation ownership and row-lock races."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy import text
from sqlmodel import select
from app.models.order import Order
from app.models.user import User
from app.models.audit_trail import AuditTrail
from app.models.enums import OrderStatus
from app.services.ai_checkout_service import AICheckoutService

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_cancel_targets_one_owned_unpaid_draft_never_current_cart():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 cache=SimpleNamespace(delete=AsyncMock(),publish=AsyncMock())
 async with sessions() as db:
  assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
  user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');other=User(email=uuid4().hex+'@example.test',hashed_password='fixture')
  db.add_all([user,other]);await db.commit()
  draft=Order(user_id=user.id);stranger=Order(user_id=other.id)
  initialized=Order(user_id=user.id,payment_transaction_id='pi_fixture');paid=Order(user_id=user.id,is_paid=True,status=OrderStatus.PROCESSING)
  db.add_all([draft,stranger,initialized,paid]);await db.commit();uid=user.id
  draft_id,stranger_id,initialized_id,paid_id=draft.id,stranger.id,initialized.id,paid.id
  service=AICheckoutService(db,cache,object(),object())
  assert (await service.handle_cancel_order({'user_id':uid}))['status']=='order_required'
  assert (await service.handle_cancel_order({'user_id':uid,'order_id':stranger_id}))['status']=='not_found'
  assert (await service.handle_cancel_order({'user_id':uid,'order_id':initialized_id}))['status']=='provider_reconciliation_required'
  assert (await service.handle_cancel_order({'user_id':uid,'order_id':paid_id}))['status']=='requires_review'
  assert (await service.handle_cancel_order({'user_id':uid,'order_id':draft_id}))['status']=='cancelled'
  assert (await service.handle_cancel_order({'user_id':uid,'order_id':draft_id}))['status']=='cancelled'
  audits=(await db.execute(select(AuditTrail).where(AuditTrail.order_id==draft_id))).scalars().all();assert len(audits)==1
 cache.delete.assert_not_awaited()
 await engine.dispose()

@pytest.mark.asyncio
async def test_cancel_waits_for_paid_state_commit_then_refuses():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  user=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add(user);await db.commit()
  order=Order(user_id=user.id);db.add(order);await db.commit();oid,uid=order.id,user.id
 cache=SimpleNamespace(delete=AsyncMock(),publish=AsyncMock())
 async with sessions() as payment:
  locked=await payment.get(Order,oid,with_for_update=True)
  async def cancel():
   async with sessions() as db:return await AICheckoutService(db,cache,object(),object()).handle_cancel_order({'user_id':uid,'order_id':oid})
  pending=asyncio.create_task(cancel());await asyncio.sleep(.05);assert not pending.done()
  locked.status=OrderStatus.PROCESSING;locked.is_paid=True;payment.add(locked);await payment.commit()
  assert (await asyncio.wait_for(pending,3))['status']=='requires_review'
 async with sessions() as db:
  current=await db.get(Order,oid);assert current.is_paid and current.status==OrderStatus.PROCESSING
 cache.delete.assert_not_awaited();await engine.dispose()
