"""Production original answer entrypoints now require current reviewed evidence."""
import asyncio,json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import select,delete,update,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from tests.test_cart_persistence_outcomes import real_cache
from app.services.ai_nlu_service import AINLUService,CommerceIntentPayload,IntentCategory,RequestContext,SearchPlan,SearchConstraints

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')
@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','changed','demo','outofstock','writer_outage','reject','source','source_missing','target_invented','cancel','customer_followup'])
@pytest.mark.parametrize('entrypoint',['synthesis','product_copy'])
async def test_actual_legacy_synthesis_current_evidence(mode,monkeypatch,entrypoint):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[];calls=[]
    try:
        async with sessions() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one().startswith('airdeliver_test_')
            row=Product(sku=('ADL-DEMO-v1-' if mode=='demo' else '')+uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,inventory=0 if mode=='outofstock' else 3,currency='USD',attributes={'material':'wood'})
            db.add(row);await db.commit();ids=[row.id]
        async def lookup(question):
            return [] if mode=='source_missing' else [{'url':'https://manufacturer.example/chair','text':'Atlas chair uses wood.'}]
        monkeypatch.setattr('app.services.product_knowledge_service.lookup_product_sources',lookup)
        async def infer(messages):
            policy=messages[0]['content'];data=json.loads(messages[1]['content']);calls.append((policy,data))
            if 'Extract only explicit' in policy:
                if mode=='cancel':raise asyncio.CancelledError()
                return '{}'
            if 'Review extracted setup' in policy:return '{"faithful":true}'
            if 'Extract source-backed' in policy:return json.dumps({'covered_targets':['Atlas chair'],'facts':[{'label':'Material','quote':'Atlas chair uses wood.','statement':'The source states wood.','source':0}]})
            if 'Review source extraction' in policy:return json.dumps(dict(supported=True,exact_model=True,product_information_only=True))
            if 'catalog_evidence' in data:
                if mode=='writer_outage':raise ConnectionError('private sentinel')
                if mode=='changed':
                    async with sessions() as writer:await writer.execute(update(Product).where(Product.id==ids[0]).values(price=999));await writer.commit()
                return json.dumps({'text':'Current catalog facts are shown in the cards. Merchant availability and suitability need verification.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=mode!='reject',all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        async with sessions() as db:
            llm=SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer));svc=AINLUService(db,SimpleNamespace(),SimpleNamespace(publish=AsyncMock()),SimpleNamespace(),llm)
            svc._get_user_dna=AsyncMock(side_effect=AssertionError('private profile must not be read'))
            svc._get_conversation_context=AsyncMock(side_effect=AssertionError('legacy history must not be read'))
            category=IntentCategory.COMPARISON if mode.startswith('source') else IntentCategory.PRICE_INQUIRY
            intent=CommerceIntentPayload(category=category,is_chitchat=False,target_products=[{'product_name':'Invented chair' if mode=='target_invented' else 'Atlas chair'}])
            request=svc._parse_incoming_message({'user_id':17,'message':'What about its price?' if mode=='customer_followup' else 'Tell me about Atlas chair'})
            if mode=='customer_followup':svc.memory.customer_context=AsyncMock(return_value=('Tell me about Atlas chair',))
            kwargs=dict(request=request,ctx=RequestContext(17,'test',0),plan=SearchPlan('chair','',SearchConstraints(clean_query='chair'),False,False),final_products=[{'id':ids[0],'name':'Untrusted old name','price':1}],ai_response_prefix='unsupported perfect match',intent_payload=intent)
            async def invoke():
                if entrypoint=='synthesis':return await svc._synthesize_response(**kwargs)
                return await svc._generate_genius_response(17,request.message_text,kwargs['final_products'][0],
                    chat_history='private hidden history',intent_payload=intent)
            if mode=='cancel':
                with pytest.raises(asyncio.CancelledError):await invoke()
            else:
                result=await invoke()
                if entrypoint=='product_copy':
                    assert 'Untrusted old name' not in result and 'private hidden history' not in result
                    if mode=='source':assert 'https://manufacturer.example/chair' in result
                    if mode in ['changed','target_invented']:assert 'could not verify' in result
                    svc._get_user_dna.assert_not_awaited();svc._get_conversation_context.assert_not_awaited();svc.rabbitmq.publish.assert_not_awaited()
                    return
                assert 'unsupported perfect match' not in result.response_text
                if mode=='source':assert 'https://manufacturer.example/chair' in result.response_text and result.products==()
                elif mode in ['ok','source_missing','customer_followup']:assert [p['id'] for p in result.products]==ids and result.products[0]['name']=='Atlas chair'
                else:assert result.products==()
            svc._get_user_dna.assert_not_awaited();svc._get_conversation_context.assert_not_awaited();svc.rabbitmq.publish.assert_not_awaited()
            assert all('USER_DNA_LOCKED' not in policy for policy,_ in calls)
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()

@pytest.mark.asyncio
async def test_customer_context_actual_redis_owner_and_role_filter(real_cache):
    from app.services.ai_nlu_service import MemoryStore,MemoryEvent,CONFIG
    cache,_=real_cache
    memory=MemoryStore(cache,CONFIG)
    await memory.append(71,MemoryEvent.create('u','Atlas chair','query'))
    await memory.append(71,MemoryEvent.create('a','Assistant invented secret product','general'))
    await memory.append(72,MemoryEvent.create('u','Other owner private product','query'))
    assert await memory.customer_context(71)==('Atlas chair',)
    assert await memory.customer_context(72)==('Other owner private product',)
    assert await memory.customer_context(73)==()
