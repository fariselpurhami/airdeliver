"""Original request categories reach the real reviewed SQL writer as task only."""
import json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.ai_nlu_service import CommerceIntentPayload,IntentCategory
from app.services.legacy_prose_boundary import reviewed_legacy_answer

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')
@pytest.mark.asyncio
@pytest.mark.parametrize('category,task,question',[
 ('SPECIFIC_SEARCH','search','Show Atlas chair'),
 ('PRICE_INQUIRY','price_inquiry','What does Atlas chair cost?'),
 ('SPECS_INQUIRY','specifications','Which material is listed for Atlas chair?'),
 ('COMPARISON','comparison','Compare the current Atlas chair facts'),
 ('BROAD_DISCOVERY','consultation','Tell me about Atlas chair'),
 ('NEGOTIATION','negotiation','Can you lower the Atlas chair price?'),
 ('OBJECTION','objection','I am unsure whether Atlas chair is right for me'),
])
async def test_actual_legacy_adapter_current_sql_and_shared_copy_task(category,task,question,monkeypatch):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);pid=None;seen=[]
    async def sources(question):return []
    monkeypatch.setattr('app.services.product_knowledge_service.lookup_product_sources',sources)
    async def infer(messages):
        policy=messages[0]['content'];data=json.loads(messages[1]['content'])
        if 'Extract only explicit' in policy:return '{}'
        if 'Review extracted setup' in policy:return '{"faithful":true}'
        if 'catalog_evidence' in data:
            seen.append(data)
            return json.dumps({'text':'The card shows current catalog facts. Suitability and any price concessions are unverified.','product_ids':[],'claims':[]})
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    try:
        async with sessions() as db:
            row=Product(sku=uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,inventory=3,currency='USD',attributes={'material':'wood'})
            db.add(row);await db.commit();pid=row.id
            intent=CommerceIntentPayload(category=IntentCategory(category),is_chitchat=False,target_products=[{'product_name':'Atlas chair'}])
            llm=SimpleNamespace(infer_sales_json=AsyncMock(side_effect=infer))
            result=await reviewed_legacy_answer(db,SimpleNamespace(),SimpleNamespace(),llm,question,[{'id':pid,'name':'STALE_NAME','price':999}],intent)
            assert [p.id for p in result.products]==[pid] and result.products[0].name=='Atlas chair'
            evidence=seen[0]['request_evidence']
            assert evidence['shopping_task']==task and evidence['exact_customer_question']==question
            assert evidence['legacy_declared_category']==category
            assert 'never commercial evidence' not in result.text
            assert 'STALE_NAME' not in json.dumps(seen)
            assert all('financial_tier' not in json.dumps(data) for data in seen)
    finally:
        async with sessions() as db:
            if pid:await db.execute(delete(Product).where(Product.id==pid));await db.commit()
        await engine.dispose()
