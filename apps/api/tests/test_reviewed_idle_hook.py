"""Explicit dormant hook, no timer/engagement wiring or provider access."""
import asyncio,json,os
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import delete,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import AINLUService

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','outage','reject','changed','cancel'])
async def test_explicit_idle_hook_real_sql_reviews_rechecks_and_publishes_or_withholds(mode):
    if not os.getenv('TEST_POSTGRES_DSN'):pytest.skip('migrated disposable PostgreSQL required')
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            row=Product(sku=uuid4().hex,name='Optional Chair',description='',category='chairs',price=20,currency='USD',inventory=3,rating=5,attributes={})
            db.add(row);await db.commit();ids=[row.id]
        calls=[]
        async def infer(messages):
            policy=messages[0]['content'];payload=json.loads(messages[1]['content']);calls.append(payload)
            if mode=='cancel':raise asyncio.CancelledError()
            if mode=='outage':raise ConnectionError('private-provider')
            if 'Extract only explicit' in policy:return '{}'
            if 'Review extracted setup' in policy:return '{"faithful":true}'
            if 'catalog_evidence' in payload:
                if mode=='changed':
                    async with sessions() as db:
                        await db.execute(update(Product).where(Product.id==ids[0]).values(inventory=0));await db.commit()
                return json.dumps({'text':'You can explore the listed choices when you want.','product_ids':[],'claims':[]})
            return json.dumps({'supported':mode!='reject','all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True})
        async with sessions() as db:
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer)))
            svc._send_to_ui=AsyncMock();svc._get_user_dna=AsyncMock(side_effect=AssertionError('No inferred profile'))
            if mode=='cancel':
                with pytest.raises(asyncio.CancelledError):await svc.handle_idle_trigger(17)
            else:
                await svc.handle_idle_trigger(17)
                if mode=='ok':
                    svc._send_to_ui.assert_awaited_once();payload=svc._send_to_ui.await_args.args[1]
                    assert payload['content']=='You can explore the listed choices when you want.'
                    assert ids[0] in [p['id'] for p in payload['products']]
                    assert svc._send_to_ui.await_args.kwargs['strict'] is True
                else:svc._send_to_ui.assert_not_awaited()
            svc._get_user_dna.assert_not_awaited()
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
