"""Run against an explicitly disposable, migrated PostgreSQL database.

Set TEST_POSTGRES_DSN to an asyncpg SQLAlchemy URL whose database name starts
with airdeliver_test_. No schema is synthesized with create_all here.
"""
import asyncio
import json
import os
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import select
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.payment_outbox import PaymentOutbox
from app.services.ai_checkout_service import AICheckoutService
from app.services.payment_orchestrator import PaymentStatus
from tests.test_ai_checkout_service import SHIPPING

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='requires disposable PostgreSQL TEST_POSTGRES_DSN')

@pytest_asyncio.fixture
async def pg_checkout():
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN'],pool_size=5,max_overflow=0)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.connect() as connection:
        name=(await connection.execute(text('SELECT current_database()'))).scalar_one()
        assert name.startswith('airdeliver_test_'), 'Refusing non-test database'
    async with sessions() as db:
        user=User(email=uuid4().hex+'@example.com',hashed_password='test-only')
        product=Product(sku=uuid4().hex,name='Shoes',description='',price='10.50',inventory=100)
        db.add_all([user,product]);await db.commit()
        uid,pid=user.id,product.id
    cache=SimpleNamespace(get_json=AsyncMock(return_value={'items':[{'product_id':pid,'name':'Shoes','price':'10.50','quantity':2}]}),publish=AsyncMock(),set_json=AsyncMock())
    gateway=SimpleNamespace(provider='stripe',transaction_id='pi_'+uuid4().hex,client_secret='test-only-secret',action_url=None)
    result=SimpleNamespace(status=PaymentStatus.SUCCESS,primary_gateway=gateway)
    async def initialize(**kwargs):
        await asyncio.sleep(0.05)
        return result
    orchestrator=SimpleNamespace(available_providers=['stripe'],process_payment=AsyncMock(side_effect=initialize))
    payload={'user_id':uid,'email':user.email,'checkout_request_id':str(uuid4()),'shipping_address':SHIPPING,'payment_provider':'stripe'}
    yield sessions,uid,pid,cache,orchestrator,payload
    async with sessions() as db:
        ids=select(Order.id).where(Order.user_id==uid)
        await db.execute(delete(PaymentOutbox).where(PaymentOutbox.order_id.in_(ids)))
        await db.execute(delete(OrderItem).where(OrderItem.order_id.in_(ids)))
        await db.execute(delete(Order).where(Order.user_id==uid))
        await db.execute(delete(Product).where(Product.id==pid))
        await db.execute(delete(User).where(User.id==uid))
        await db.commit()
    await engine.dispose()

@pytest.mark.asyncio
async def test_migrated_postgres_can_create_utc_user_product_and_checkout(pg_checkout):
    sessions,uid,pid,cache,orchestrator,payload=pg_checkout
    async with sessions() as db:
        result=await AICheckoutService(db,cache,AsyncMock(),orchestrator).handle_confirm_order(payload)
        assert result['status']=='ready'
        order=(await db.execute(select(Order).where(Order.user_id==uid))).scalars().one()
        assert order.created_at.tzinfo is not None
        assert abs((datetime.now(timezone.utc)-order.created_at).total_seconds())<10
        assert order.payment_transaction_id.startswith('pi_')
        assert result['payment']['checkout_request_id']==payload['checkout_request_id']

@pytest.mark.asyncio
async def test_two_independent_postgres_transactions_create_one_checkout(pg_checkout):
    sessions,uid,pid,cache,orchestrator,payload=pg_checkout
    entered=0
    both=asyncio.Event()
    original=cache.get_json.return_value
    async def cart(_):
        nonlocal entered
        entered+=1
        if entered==2: both.set()
        await asyncio.wait_for(both.wait(),timeout=5)
        return json.loads(json.dumps(original))
    cache.get_json.side_effect=cart
    async def checkout():
        async with sessions() as db:
            return await AICheckoutService(db,cache,AsyncMock(),orchestrator).handle_confirm_order(payload)
    results=await asyncio.wait_for(asyncio.gather(checkout(),checkout()),timeout=10)
    assert all(result['status'] in {'ready','pending'} for result in results)
    async with sessions() as db:
        orders=(await db.execute(select(Order).where(Order.user_id==uid))).scalars().all()
        assert len(orders)==1
    assert orchestrator.process_payment.await_count==1

@pytest.mark.asyncio
async def test_new_process_replays_committed_handoff_without_cart_or_gateway(pg_checkout):
    sessions,uid,pid,cache,orchestrator,payload=pg_checkout
    async with sessions() as db:
        first=await AICheckoutService(db,cache,AsyncMock(),orchestrator).handle_confirm_order(payload)
    cache.get_json.side_effect=AssertionError('replay must not reload mutable cart')
    orchestrator.process_payment.side_effect=AssertionError('replay must not create another intent')
    async with sessions() as db:
        second=await AICheckoutService(db,cache,AsyncMock(),orchestrator).handle_confirm_order(payload)
    assert second==first

@pytest.mark.asyncio
async def test_timestamp_readback_is_verified_from_a_new_session(pg_checkout):
    sessions,uid,pid,cache,orchestrator,payload=pg_checkout
    async with sessions() as db:
        result=await AICheckoutService(db,cache,AsyncMock(),orchestrator).handle_confirm_order(payload)
        order_id=result['order_id']
    async with sessions() as db:
        order=await db.get(Order,order_id)
        native=(await db.execute(text("SELECT data_type FROM information_schema.columns WHERE table_name='orders' AND column_name='created_at'"))).scalar_one()
        assert native=='timestamp with time zone'
        assert order.created_at.tzinfo is not None
        assert abs((datetime.now(timezone.utc)-order.created_at).total_seconds())<10


@pytest.mark.asyncio
async def test_populated_legacy_timestamps_require_a_verified_zone_and_preserve_instants(pg_checkout,monkeypatch):
    from alembic import command
    from alembic.config import Config
    sessions,uid,_,_,_,_=pg_checkout
    monkeypatch.setenv('DATABASE_URI',os.environ['TEST_POSTGRES_DSN'])
    monkeypatch.delenv('LEGACY_TIMESTAMP_TIMEZONE',raising=False)
    async with sessions() as db:
        original=(await db.execute(text('SELECT created_at FROM users WHERE id=:id'),{'id':uid})).scalar_one()
        await db.execute(text("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"))
        await db.commit()
    await asyncio.to_thread(command.stamp,Config('alembic.ini'),'d74fe213c654')
    with pytest.raises(Exception,match='explicit LEGACY_TIMESTAMP_TIMEZONE'):
        await asyncio.to_thread(command.upgrade,Config('alembic.ini'),'head')
    monkeypatch.setenv('LEGACY_TIMESTAMP_TIMEZONE','UTC')
    await asyncio.to_thread(command.upgrade,Config('alembic.ini'),'head')
    async with sessions() as db:
        restored=(await db.execute(text('SELECT created_at FROM users WHERE id=:id'),{'id':uid})).scalar_one()
        assert restored==original


@pytest.mark.asyncio
async def test_already_aware_columns_are_not_reinterpreted_on_migration_replay(pg_checkout,monkeypatch):
    from alembic import command
    from alembic.config import Config
    sessions,uid,_,_,_,_=pg_checkout
    monkeypatch.setenv('DATABASE_URI',os.environ['TEST_POSTGRES_DSN'])
    async with sessions() as db:
        original=(await db.execute(text('SELECT created_at FROM users WHERE id=:id'),{'id':uid})).scalar_one()
    monkeypatch.setenv('LEGACY_TIMESTAMP_TIMEZONE','America/Los_Angeles')
    await asyncio.to_thread(command.stamp,Config('alembic.ini'),'d74fe213c654')
    await asyncio.to_thread(command.upgrade,Config('alembic.ini'),'head')
    async with sessions() as db:
        restored=(await db.execute(text('SELECT created_at FROM users WHERE id=:id'),{'id':uid})).scalar_one()
        assert restored==original
