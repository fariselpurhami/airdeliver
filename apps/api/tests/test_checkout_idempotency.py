"""Real ORM boundaries for request replay and persisted payment intent identity."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

@compiles(JSONB, "sqlite")
def sqlite_jsonb_for_contract_tests(type_, compiler, **kw):
    return "JSON"

from sqlalchemy.orm import Session
from sqlmodel import select
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.enums import OrderStatus
from app.services.ai_checkout_service import AICheckoutService
from app.services.payment_orchestrator import PaymentStatus
from tests.test_ai_checkout_service import CART, CONFIRM

KEY='a02cf0a7-67a1-4dcc-96d6-45b7be67d306'
PAYLOAD={**CONFIRM, 'checkout_request_id':KEY, 'payment_provider':'stripe'}

class Adapter:
    def __init__(self,session): self.session=session
    def add(self,value): self.session.add(value)
    def add_all(self,values): self.session.add_all(values)
    async def execute(self,statement): return self.session.execute(statement)
    async def get(self,*args,**kwargs): return self.session.get(*args,**kwargs)
    async def flush(self): self.session.flush()
    async def commit(self): self.session.commit()
    async def refresh(self,value): self.session.refresh(value)
    async def rollback(self): self.session.rollback()

@pytest.fixture
def checkout():
    engine=create_engine('sqlite://')
    for model in (Order, OrderItem, Product): model.__table__.create(engine)
    with Session(engine,expire_on_commit=False) as session:
        session.add(Product(id=7,sku='test',name='Shoes',description='',price='10.50',inventory=99))
        session.commit()
        cache=SimpleNamespace(get_json=AsyncMock(return_value=json.loads(json.dumps(CART))),publish=AsyncMock(),set_json=AsyncMock())
        gateway=SimpleNamespace(provider='stripe',transaction_id='pi_existing',client_secret='secret_for_test',action_url=None)
        orchestrator=SimpleNamespace(available_providers=['stripe'],process_payment=AsyncMock(return_value=SimpleNamespace(status=PaymentStatus.SUCCESS,primary_gateway=gateway)))
        service=AICheckoutService(Adapter(session),cache,AsyncMock(),orchestrator)
        yield service,session,cache,orchestrator
    engine.dispose()

@pytest.mark.asyncio
async def test_same_request_replays_one_order_and_one_provider_initialization(checkout):
    service,session,cache,orchestrator=checkout
    first=await service.handle_confirm_order(PAYLOAD)
    cache.get_json.return_value={'items':[]}
    second=await service.handle_confirm_order(PAYLOAD)
    assert first['status'] == second['status'] == 'ready'
    assert first['payment'] == second['payment']
    assert len(session.execute(select(Order)).scalars().all()) == 1
    assert orchestrator.process_payment.await_count == 1

@pytest.mark.asyncio
async def test_reusing_request_with_different_shipping_is_a_conflict(checkout):
    service,session,cache,orchestrator=checkout
    await service.handle_confirm_order(PAYLOAD)
    changed={**PAYLOAD,'shipping_address':{**PAYLOAD['shipping_address'],'line1':'456 Another Street'}}
    result=await service.handle_confirm_order(changed)
    assert result['status'] == 'conflict'
    assert len(session.execute(select(Order)).scalars().all()) == 1
    assert orchestrator.process_payment.await_count == 1

@pytest.mark.asyncio
async def test_unknown_provider_outcome_retries_the_identical_frozen_request(checkout):
    service,session,cache,orchestrator=checkout
    success=orchestrator.process_payment.return_value
    orchestrator.process_payment.side_effect=asyncio.TimeoutError()
    first=await service.handle_confirm_order(PAYLOAD)
    original=orchestrator.process_payment.call_args.kwargs['request'].model_dump(mode='json')
    assert first['status']=='pending'
    cache.get_json.return_value={'items':[]}
    product=session.get(Product,7);product.price='99.00';session.commit()
    orchestrator.process_payment.side_effect=None
    orchestrator.process_payment.return_value=success
    second=await service.handle_confirm_order(PAYLOAD)
    assert second['status']=='ready'
    assert original==orchestrator.process_payment.call_args.kwargs['request'].model_dump(mode='json')
    assert second['payment']['order_data']['total']==21.0
    assert len(session.execute(select(Order)).scalars().all())==1

@pytest.mark.asyncio
async def test_active_lease_never_calls_the_provider_a_second_time(checkout):
    service,session,cache,orchestrator=checkout
    orchestrator.process_payment.side_effect=asyncio.TimeoutError()
    await service.handle_confirm_order(PAYLOAD)
    order=session.execute(select(Order)).scalars().one()
    order.payment_setup_lease_until=datetime.now(timezone.utc)+timedelta(seconds=20)
    session.commit()
    before=orchestrator.process_payment.await_count
    assert (await service.handle_confirm_order(PAYLOAD))['status']=='pending'
    assert orchestrator.process_payment.await_count==before

@pytest.mark.asyncio
async def test_expired_lease_can_be_reconciled_with_the_original_provider_key(checkout):
    service,session,cache,orchestrator=checkout
    success=orchestrator.process_payment.return_value
    orchestrator.process_payment.side_effect=asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError): await service.handle_confirm_order(PAYLOAD)
    order=session.execute(select(Order)).scalars().one()
    first_key=order.checkout_data['payment_request']['idempotency_key']
    order.payment_setup_lease_until=datetime.now(timezone.utc)-timedelta(seconds=1)
    session.commit()
    orchestrator.process_payment.side_effect=None
    orchestrator.process_payment.return_value=success
    assert (await service.handle_confirm_order(PAYLOAD))['status']=='ready'
    assert orchestrator.process_payment.call_args.kwargs['request'].idempotency_key==first_key
    assert order.payment_setup_generation==2

@pytest.mark.asyncio
async def test_retry_outside_conservative_provider_window_never_posts_again(checkout):
    service,session,cache,orchestrator=checkout
    await service.handle_confirm_order(PAYLOAD)
    order=session.execute(select(Order)).scalars().one()
    order.created_at=datetime.now(timezone.utc)-timedelta(hours=2);session.commit()
    result=await service.handle_confirm_order(PAYLOAD)
    assert result['status']=='reconciliation_required'
    assert 'payment' not in result
    assert orchestrator.process_payment.await_count==1

@pytest.mark.asyncio
@pytest.mark.parametrize('paid,canceled,expected',[(True,False,'paid'),(False,True,'reconciliation_required')])
async def test_settled_or_canceled_order_cannot_reopen_checkout(checkout,paid,canceled,expected):
    service,session,cache,orchestrator=checkout
    await service.handle_confirm_order(PAYLOAD)
    order=session.execute(select(Order)).scalars().one()
    order.is_paid=paid
    if canceled: order.status=OrderStatus.CANCELLED
    session.commit()
    result=await service.handle_confirm_order(PAYLOAD)
    assert result['status']==expected and 'payment' not in result
    assert orchestrator.process_payment.await_count==1

@pytest.mark.asyncio
async def test_late_provider_response_cannot_overwrite_newer_claim(checkout):
    service,session,cache,orchestrator=checkout
    success=orchestrator.process_payment.return_value
    async def late_result(**kwargs):
        order=session.execute(select(Order)).scalars().one()
        order.payment_setup_generation+=1
        session.commit()
        return success
    orchestrator.process_payment.side_effect=late_result
    result=await service.handle_confirm_order(PAYLOAD)
    order=session.execute(select(Order)).scalars().one()
    assert result['status']=='pending'
    assert order.payment_transaction_id is None
    assert 'handoff' not in order.checkout_data

@pytest.mark.asyncio
async def test_cancellation_during_provider_io_never_exposes_payment_tokens(checkout):
    service,session,cache,orchestrator=checkout
    success=orchestrator.process_payment.return_value
    async def cancel_during_call(**kwargs):
        order=session.execute(select(Order)).scalars().one()
        order.status=OrderStatus.CANCELLED;session.commit()
        return success
    orchestrator.process_payment.side_effect=cancel_during_call
    result=await service.handle_confirm_order(PAYLOAD)
    assert result['status']=='reconciliation_required' and 'payment' not in result
    assert session.execute(select(Order)).scalars().one().payment_transaction_id is None

@pytest.mark.asyncio
async def test_request_keys_are_scoped_to_the_authenticated_account(checkout):
    service,session,cache,orchestrator=checkout
    await service.handle_confirm_order(PAYLOAD)
    await service.handle_confirm_order({**PAYLOAD,'user_id':2})
    orders=session.execute(select(Order).order_by(Order.id)).scalars().all()
    assert len(orders)==2
    assert orders[0].checkout_data['payment_request']['idempotency_key'] != orders[1].checkout_data['payment_request']['idempotency_key']


def test_unique_checkout_constraint_is_enforced_by_the_database(checkout):
    from sqlalchemy.exc import IntegrityError
    _,session,_,_=checkout
    session.add(Order(user_id=1,checkout_request_id=KEY));session.commit()
    session.add(Order(user_id=1,checkout_request_id=KEY))
    with pytest.raises(IntegrityError): session.commit()
    session.rollback()
    # Legacy rows with no checkout key remain valid, without invented identities.
    session.add_all([Order(user_id=1),Order(user_id=1)]);session.commit()
