"""Real SQL consent recheck before retained answer publication."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select
from app.models.product import Product
from app.services.customer_memory_service import CustomerMemoryService
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
@pytest.mark.parametrize('entry',['catalog','source','setup'])
async def test_saved_hints_revoked_during_model_are_not_published(memory_db,monkeypatch,entry):
    sessions,(uid,_)=memory_db;pid=None
    async with sessions() as db:
        memory=CustomerMemoryService(db);await memory.set_consent(uid,True)
        assert await memory.collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'})))
        row=Product(sku=uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,currency='USD',inventory=3,attributes={})
        db.add(row);await db.commit();pid=row.id
    monkeypatch.setattr('app.services.product_knowledge_service.lookup_product_sources',AsyncMock(return_value=[{'url':'https://maker.example/chair','text':'Atlas chair uses wood.'}]))
    revoked=False
    async def infer(messages):
        nonlocal revoked
        policy=messages[0]['content'];data=json.loads(messages[1]['content'])
        if 'Extract only explicit' in policy:return '{}'
        if 'Review extracted setup' in policy:return '{"faithful":true}'
        if 'Plan generic' in policy:return '{"components":["chair"]}'
        if 'Review a generic' in policy:return '{"appropriate":true,"no_invented_products":true}'
        if ('catalog_evidence' in data or 'Extract source-backed' in policy) and not revoked:
            async with sessions() as db:await CustomerMemoryService(db).set_consent(uid,False)
            revoked=True
        if 'Extract source-backed' in policy:return json.dumps({'covered_targets':['Atlas chair'],'facts':[{'label':'Material','quote':'Atlas chair uses wood.','source':0}]})
        if 'Review source extraction' in policy:return '{"supported":true,"exact_model":true,"product_information_only":true}'
        if 'catalog_evidence' in data:return '{"text":"PRIVATE_PERSONALIZED_ANSWER","product_ids":[],"claims":[]}'
        return '{"supported":true,"all_product_mentions_declared":true,"no_unsupported_commercial_claims":true,"fulfills_discovery_task":true}'
    try:
        async with sessions() as db:
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer)))
            async def retrieve(session,query,**kw):return (await session.execute(select(Product).where(Product.id==pid))).scalars().all()
            svc.search_engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve));svc.memory.customer_context=AsyncMock(return_value=('Atlas chair',))
            if entry=='setup':
                from app.services.ai_nlu_service import RequestContext
                svc._send_to_ui=AsyncMock();request=svc._parse_incoming_message({'user_id':uid,'message':'Build a chair setup'})
                await svc._handle_ecosystem_building(request,RequestContext(uid,'test',0),CommerceIntentPayload(category=IntentCategory.ECOSYSTEM_BUILDER,is_chitchat=False))
                result=svc._send_to_ui.await_args.args[1]['content']
            else:result=await svc._generate_genius_response(uid,'Atlas chair',{'id':pid},intent_payload=CommerceIntentPayload(category=IntentCategory.COMPARISON if entry=='source' else IntentCategory.SPECIFIC_SEARCH,is_chitchat=False,target_products=[{'product_name':'Atlas chair'}]))
            assert revoked and 'PRIVATE_PERSONALIZED' not in result and 'https://maker.example' not in result
            assert result.startswith('I could not verify')
    finally:
        async with sessions() as db:await db.execute(delete(Product).where(Product.id==pid));await db.commit()
