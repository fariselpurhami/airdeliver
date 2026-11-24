"""Arabic literal scope through real SQL retrieval, writer/review and stale gate.

Controlled extraction outputs test boundary semantics, not live LLM translation.
"""
import json,os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import delete,select,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.product import Product
from app.services.neural_core_service import NeuralCoreService,RouterDecision,SearchTarget,SessionMemory
from app.services.shopping_discovery import ShoppingBrief

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='migrated disposable PostgreSQL required')

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['ok','wrong_ram','scope_reject','invented_target','changed'])
@pytest.mark.parametrize('feature',['على الأقل ١٦ جيجابايت رام','١٦ جيجابايت رام على الأقل'])
async def test_arabic_per_target_scope_current_sql_and_reviewed_publication(mode,feature):
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False);ids=[];seen=[]
    target='لابتوب';other='كرسي';exclusion='أحمر'
    message=f'عايز {target} {feature} و {other} بدون {exclusion}'
    try:
        async with sessions() as db:
            rows=[Product(sku=uuid4().hex,name='لابتوب أطلس',description='',category='electronics',price=20,currency='USD',inventory=3,attributes={'RAM':'8GB' if mode=='wrong_ram' else '32GB'}),Product(sku=uuid4().hex,name='كرسي أطلس',description='',category='chairs',price=20,currency='USD',inventory=3,attributes={'color':'أزرق'})]
            db.add_all(rows);await db.commit();ids=[r.id for r in rows]
        async def retrieve(db,query,**kwargs):
            result=await db.execute(select(Product).where(Product.id.in_(ids),Product.name.ilike('%'+query+'%')))
            return result.scalars().all()
        svc=object.__new__(NeuralCoreService);svc.ai_engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=retrieve));svc.cache=SimpleNamespace();svc.is_healthy=True
        async def infer(messages):
            prompt=messages[0]['content'];data=json.loads(messages[1]['content'])
            if 'Assign existing hard features' in prompt:
                kind=data['constraint_kind'];name=target if kind=='required_features' else other
                return json.dumps({'assignments':[{'target':'invented' if mode=='invented_target' else name,'features':[feature if kind=='required_features' else exclusion]}]})
            if 'Review exact target/feature scope' in prompt:return json.dumps({'explicit_scope':mode!='scope_reject'})
            if 'catalog_evidence' in data:
                seen.append(data)
                if mode=='changed':
                    async with sessions() as writer:
                        await writer.execute(update(Product).where(Product.id==ids[0]).values(attributes={'RAM':'8GB'}));await writer.commit()
                return json.dumps({'text':'الكروت فيها بيانات الكتالوج الحالية. الملاءمة والتوافق محتاجين تحقق.','product_ids':[],'claims':[]})
            return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
        svc._execute_llm_inference=infer
        memory=SessionMemory(user_name='test')
        decision=RouterDecision(intent='PRODUCT_SEARCH',targets=[SearchTarget(product_name=target),SearchTarget(product_name=other)])
        brief=ShoppingBrief(required_features=[feature],excluded_terms=[exclusion]).grounded(message)
        async with sessions() as db:
            result=await svc._handle_scoped_target_search(db,decision,brief,message,memory)
        if mode in {'scope_reject','invented_target'}:
            assert result.response_kind=='clarification' and result.products==[] and not seen
            svc.ai_engine.perform_hybrid_search_pure.assert_not_awaited()
            assert memory.target_requirements=={} and memory.target_exclusions=={}
        elif mode=='changed':
            assert result.response_kind=='system_notice' and result.products==[]
            assert memory.target_requirements=={} and memory.target_exclusions=={}
        else:
            assert [c.id for c in result.products]==(ids[1:] if mode=='wrong_ram' else ids)
            assert memory.target_requirements=={target:[feature]} and memory.target_exclusions=={other:[exclusion]}
            assert [t['target'] for t in seen[0]['request_evidence']['target_searches']]==[target,other]
            assert all(c.name!='invented' for c in result.products)
    finally:
        async with sessions() as db:
            if ids:await db.execute(delete(Product).where(Product.id.in_(ids)));await db.commit()
        await engine.dispose()
