"""Typed ordinary advisory tasks reach real SQL evidence, no extra model stage."""
import json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,SessionMemory

@pytest.mark.asyncio
@pytest.mark.parametrize('task,question',[
 ('price_inquiry','What is the listed price of Atlas chair?'),
 ('negotiation','Can you reduce the Atlas chair price?'),
 ('objection','I am unsure about Atlas chair material.'),
])
@pytest.mark.parametrize('targets',[True,False])
async def test_ordinary_typed_advice_current_sql_writer_question(task,question,targets):
    if not os.getenv('TEST_POSTGRES_DSN'):pytest.skip('migrated disposable PostgreSQL required')
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);pid=None;seen=[]
    try:
        async with sessions() as db:
            row=Product(sku=uuid4().hex,name='Atlas chair',description='',category='chairs',price=20,currency='USD',inventory=3,attributes={'material':'wood'})
            db.add(row);await db.commit();pid=row.id
        async def search(db,query,**kwargs):return (await db.execute(select(Product).where(Product.id==pid))).scalars().all()
        svc=NeuralCoreService(SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=search)),SimpleNamespace());svc.is_healthy=True;svc.configuration_error=False
        async def infer(messages):
            if 'primary cognitive routing' in messages[0]['content']:
                return json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas chair','search_subject':'Atlas chair','shopping_task':task,'targets':[{'product_name':'Atlas chair'}] if targets else []})
            data=json.loads(messages[1]['content'])
            if 'catalog_evidence' in data:
                seen.append(data)
                return json.dumps({'text':'The card shows listed catalog facts. Concessions and suitability are unverified.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=AsyncMock(side_effect=infer)
        decision=await svc._analyze_intent(question,SessionMemory(user_name='test'))
        assert decision.shopping_task==task
        async with sessions() as db:
            if targets:result=await svc._handle_staged_product_search(db,decision,decision.brief,question)
            else:result=await svc._handle_product_search(db,'Atlas chair',decision.brief,question,decision)
        assert [p.id for p in result.products]==[pid] and result.action is None
        assert seen[0]['request_evidence']['shopping_task']==task
        assert seen[0]['request_evidence']['exact_customer_question']==question
        assert svc._execute_llm_inference.await_count==3
    finally:
        async with sessions() as db:
            if pid:await db.execute(delete(Product).where(Product.id==pid));await db.commit()
        await engine.dispose()
