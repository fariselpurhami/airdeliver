"""Original setup entrypoint, real disposable SQL, controlled model/search."""
import asyncio,json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import select,delete,update,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory,RequestContext

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable migrated PostgreSQL required')

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','changed','demo','plan_reject','budget_invented','budget_omitted','writer_outage','cancel','review_number','out_of_stock','over_budget'])
async def test_original_ecosystem_shared_current_evidence(mode):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            rows=[Product(sku=('ADL-DEMO-v1-' if mode=='demo' else '')+uuid4().hex,name=n,description='',category=n,price=200 if mode=='over_budget' else 20,inventory=0 if mode=='out_of_stock' else 3,currency='USD',attributes={}) for n in ['desk','chair']]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        queries=[];calls=[]
        async def search(db,query,**kwargs):
            queries.append(query)
            return (await db.execute(select(Product).where(Product.id.in_(ids),Product.name==query))).scalars().all()
        async def infer(messages):
            policy=messages[0]['content'];calls.append(policy)
            if 'Extract only explicit' in policy:
                if mode=='cancel':raise asyncio.CancelledError()
                return json.dumps({'budget':'USD 100' if mode!='budget_invented' else 'USD 1000','budget_max':'100' if mode!='budget_invented' else '1000','budget_currency':'USD'}) if mode!='budget_omitted' else '{}'
            if 'Review extracted setup' in policy:return json.dumps({'faithful':1 if mode=='review_number' else mode!='budget_omitted'})
            if 'Plan generic' in policy:return json.dumps({'components':['desk','chair']})
            if 'Review a generic' in policy:return json.dumps({'appropriate':mode!='plan_reject','no_invented_products':True})
            payload=json.loads(messages[1]['content'])
            if 'catalog_evidence' in payload:
                if mode=='writer_outage':raise ConnectionError('private sentinel')
                if mode=='changed':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(price=999));await writer.commit()
                return json.dumps({'text':'Possible components are shown in the cards. Compatibility and completeness are not verified.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        llm=SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer))
        async with sessions() as db:
            svc=AINLUService(db,SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=search)),SimpleNamespace(publish=AsyncMock()),SimpleNamespace(),llm)
            svc._send_to_ui=AsyncMock();svc._save_conversation_turn=AsyncMock()
            request=svc._parse_incoming_message({'user_id':17,'message':'Build a desk and chair setup under USD 100'})
            intent=CommerceIntentPayload(category=IntentCategory.ECOSYSTEM_BUILDER,is_chitchat=False,budget_max=99999)
            if mode=='cancel':
                with pytest.raises(asyncio.CancelledError):await svc._handle_ecosystem_building(request,RequestContext(17,'test',0),intent)
                svc._send_to_ui.assert_not_awaited()
            else:
                await svc._handle_ecosystem_building(request,RequestContext(17,'test',0),intent)
                payload=svc._send_to_ui.await_args.args[1]
                if mode=='ok':assert {p['id'] for p in payload['products']}==set(ids)
                else:assert payload.get('products',[])==[]
            svc.rabbitmq.publish.assert_not_awaited();svc._save_conversation_turn.assert_not_awaited()
            if mode in ['plan_reject','budget_invented','budget_omitted','cancel','review_number']:assert queries==[]
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
