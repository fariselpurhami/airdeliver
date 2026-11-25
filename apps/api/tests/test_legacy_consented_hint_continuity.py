"""Real SQL consent hints reach retained answer callers, not product proof."""
import json
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,update,select
from app.models.product import Product
from app.models.customer_memory import CustomerShoppingMemory
from app.services.customer_memory_service import CustomerMemoryService
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
@pytest.mark.parametrize('entry',['catalog','source','setup'])
@pytest.mark.parametrize('state',['enabled','other_owner','expired','revoked'])
async def test_retained_product_answer_real_consent_and_current_sql(memory_db,state,entry,monkeypatch):
    sessions,(uid,other)=memory_db;pid=None;seen=[]
    async def source(question):return [{'url':'https://manufacturer.example/chair','text':'Atlas chair uses wood.'}]
    monkeypatch.setattr('app.services.product_knowledge_service.lookup_product_sources',source)
    try:
        async with sessions() as db:
            memory=CustomerMemoryService(db);await memory.set_consent(uid,True)
            assert await memory.collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'})))
            if state=='revoked':await memory.erase_preferences(uid)
            if state=='expired':
                await db.execute(update(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==uid).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
            row=Product(sku=uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,currency='USD',inventory=3,attributes={})
            db.add(row);await db.commit();pid=row.id
        async def infer(messages):
            policy=messages[0]['content'];data=json.loads(messages[1]['content'])
            if 'Extract only explicit' in policy:
                assert 'consented_saved_preferences' not in data
                return '{}'
            if 'Review extracted setup' in policy:return '{"faithful":true}'
            if 'Plan generic' in policy:return json.dumps({'components':['chair']})
            if 'Review a generic' in policy:return json.dumps({'appropriate':True,'no_invented_products':True})
            if 'Extract source-backed' in policy:
                seen.append({'request_evidence':data,'customer_brief':{'required_features':[]}})
                return json.dumps({'covered_targets':['Atlas chair'],'facts':[{'label':'Material','quote':'Atlas chair uses wood.','statement':'The source states wood.','source':0}]})
            if 'Review source extraction' in policy:return json.dumps(dict(supported=True,exact_model=True,product_information_only=True))
            if 'catalog_evidence' in data:
                seen.append(data)
                return json.dumps({'text':'Current catalog details are shown. Preferences do not prove suitability.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        async with sessions() as db:
            svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(),SimpleNamespace(),SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer)))
            async def retrieve(session,query,**kwargs):return (await session.execute(select(Product).where(Product.id==pid))).scalars().all()
            svc.search_engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve))
            svc.memory.customer_context=AsyncMock(return_value=('Tell me about Atlas chair',))
            svc._get_user_dna=AsyncMock(side_effect=AssertionError('No inferred profile'))
            if entry=='setup':
                from app.services.ai_nlu_service import RequestContext
                svc._send_to_ui=AsyncMock()
                request=svc._parse_incoming_message({'user_id':other if state=='other_owner' else uid,'message':'Build a chair setup'})
                await svc._handle_ecosystem_building(request,RequestContext(request.user_id,'test',0),CommerceIntentPayload(category=IntentCategory.ECOSYSTEM_BUILDER,is_chitchat=False))
                text=svc._send_to_ui.await_args.args[1]['content']
            else:
                text=await svc._generate_genius_response(other if state=='other_owner' else uid,'Atlas chair',{'id':pid},intent_payload=CommerceIntentPayload(category=IntentCategory.SPECIFIC_SEARCH if entry=='catalog' else IntentCategory.COMPARISON,is_chitchat=False,target_products=[{'product_name':'Atlas chair'}]))
            assert text.startswith('Current catalog') if entry!='source' else 'https://manufacturer.example/chair' in text
            evidence=seen[0]['request_evidence']
            assert evidence.get('consented_saved_preferences',[])==(['Customer explicitly prefers color: blue'] if state=='enabled' else [])
            assert seen[0]['customer_brief']['required_features']==[]
            svc._get_user_dna.assert_not_awaited()
    finally:
        async with sessions() as db:
            if pid:await db.execute(delete(Product).where(Product.id==pid));await db.commit()
