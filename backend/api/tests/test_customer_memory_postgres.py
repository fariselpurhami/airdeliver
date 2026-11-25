# Historical retained-method contracts. New production bridge is tested separately.
"""Real PostgreSQL consent/dedupe/retention/self-service boundaries."""
import os
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete,select,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.core.config import get_core_settings
from app.models.user import User
from app.models.customer_memory import CustomerMemoryConsent,CustomerShoppingMemory
from app.services.customer_memory_service import CustomerMemoryService,valid_candidate


@pytest.mark.parametrize('candidate,source',[
    ({'category':'health','value':'diabetes','evidence':'I prefer diabetes'},'I prefer diabetes'),
    ({'category':'color','value':'blue','evidence':'I prefer blue'},'Customer says unrelated text'),
    ({'category':'style','value':'rich','evidence':'I prefer rich'},'I prefer rich'),
    ({'category':'color','value':'blue','evidence':'I do not like blue'},'I do not like blue'),
    ({'category':'color','value':'blue','evidence':'She prefers blue'},'She prefers blue'),
])
def test_sensitive_inferred_unattributed_or_negative_candidates_are_rejected(candidate,source):
    assert valid_candidate(candidate,source) is None


@pytest_asyncio.fixture
async def memory_db(monkeypatch):
    if not os.getenv('TEST_POSTGRES_DSN'):pytest.skip('real migrated PostgreSQL required')
    settings=get_core_settings();monkeypatch.setattr(settings,'CUSTOMER_MEMORY_ENABLED',True)
    engine=create_async_engine(os.environ['TEST_POSTGRES_DSN'])
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with sessions() as db:
        users=[User(email=uuid4().hex+'@example.com',hashed_password='local-test-only') for _ in range(2)]
        db.add_all(users);await db.commit()
    yield sessions,[u.id for u in users]
    async with sessions() as db:
        for model in [CustomerShoppingMemory,CustomerMemoryConsent]:
            await db.execute(delete(model).where(model.user_id.in_([u.id for u in users])))
        await db.execute(delete(User).where(User.id.in_([u.id for u in users])));await db.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_real_pg_no_consent_no_extractor_or_memory_then_optin_dedupe_recall_and_revoke(memory_db):
    sessions,(uid,other)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db)
        assert not await service.collect(uid,'I prefer blue',llm)
        llm.extract_shopping_preferences.assert_not_awaited()
        await service.set_consent(uid,True)
        assert await service.collect(uid,'I prefer blue',llm)
        assert await service.collect(uid,'I prefer blue',llm)
    # New session proves persistent recall, not in-process state.
    async with sessions() as db:
        service=CustomerMemoryService(db)
        assert await service.recall(uid)==['Customer explicitly prefers color: blue']
        assert await service.recall(other)==[]
        exported=await service.export(uid)
        assert len(exported['preferences'])==1 and exported['retention_days'] is None
        await service.set_consent(uid,False)
        assert await service.recall(uid)==['Customer explicitly prefers color: blue']
        assert len((await service.export(uid))['preferences'])==1
        assert not await service.collect(uid,'I prefer blue',llm)


@pytest.mark.asyncio
async def test_real_pg_expired_memory_excluded_and_physically_purged(memory_db):
    sessions,(uid,_)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'style','value':'classic','evidence':'I prefer classic'}))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        await service.collect(uid,'I prefer classic',llm)
        await db.execute(update(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==uid).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
        assert await service.recall(uid)==[]
        assert (await service.export(uid))['preferences']==[]
        await service.purge_expired()
        assert (await db.execute(select(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==uid))).scalars().all()==[]


@pytest.mark.asyncio
async def test_real_pg_feature_off_does_not_extract_or_recall(memory_db,monkeypatch):
    sessions,(uid,_)=memory_db
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        monkeypatch.setattr(get_core_settings(),'CUSTOMER_MEMORY_ENABLED',False)
        llm=SimpleNamespace(extract_shopping_preferences=AsyncMock())
        assert not await service.collect(uid,'I prefer blue',llm)
        assert await service.recall(uid)==[]
        llm.extract_shopping_preferences.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_pg_preference_reaches_new_nlu_instance_answer_context(memory_db):
    from app.services.ai_nlu_service import AINLUService
    sessions,(uid,_)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}),generate_response=AsyncMock(return_value='Listed catalog answer'))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        await service.collect(uid,'I prefer blue',llm)
    async with sessions() as db:
        nlu=AINLUService(db,SimpleNamespace(),object(),SimpleNamespace(),llm)
        nlu.memory.get_context=AsyncMock(return_value='')
        nlu._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='explorer',tier='MEDIUM'))
        nlu._safe_web_search=AsyncMock(return_value='')
        context=await nlu._get_conversation_context(uid)
        assert 'color: blue' in context
        await nlu._generate_genius_response_legacy_unreviewed(uid,'headphones',{'id':7,'name':'headphones','price':10},context)
        call=llm.generate_response.call_args.kwargs
        assert 'color: blue' in call['prompt']
        assert 'color: blue' not in call['system_role']


@pytest.mark.asyncio
async def test_revocation_while_extraction_waits_cannot_reinsert_memory(memory_db):
    import asyncio
    sessions,(uid,_)=memory_db
    started=asyncio.Event();resume=asyncio.Event()
    async def extractor(text):
        started.set();await resume.wait()
        return {'category':'color','value':'blue','evidence':'I prefer blue'}
    async with sessions() as db:
        await CustomerMemoryService(db).set_consent(uid,True)
    async with sessions() as collection_db:
        task=asyncio.create_task(CustomerMemoryService(collection_db).collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=extractor)))
        await started.wait()
        async with sessions() as revoke_db:
            await CustomerMemoryService(revoke_db).set_consent(uid,False)
        resume.set()
        assert not await task
    async with sessions() as db:
        assert await CustomerMemoryService(db).recall(uid)==[]
        assert (await CustomerMemoryService(db).export(uid))['preferences']==[]

@pytest.mark.asyncio
async def test_optional_recall_failure_rolls_back_real_postgres_session(memory_db,monkeypatch):
    from sqlalchemy import text
    from app.services.ai_nlu_service import AINLUService
    sessions,(uid,_)=memory_db
    async with sessions() as db:
        async def fail_recall(self,user_id):
            await self.db.execute(text('SELECT * FROM missing_optional_memory_table_for_test'))
        monkeypatch.setattr(CustomerMemoryService,'recall',fail_recall)
        service=SimpleNamespace(db=db,memory=SimpleNamespace(get_context=AsyncMock(return_value='recent context')),
            config=SimpleNamespace(context_window_size=5))
        result=await AINLUService._get_conversation_context(service,uid)
        assert result=='recent context'
        assert (await db.execute(text('SELECT 1'))).scalar_one()==1
