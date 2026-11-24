"""Canonical SQL consent generation protects stale async work and reads."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import update
from app.models.customer_memory import CustomerMemoryConsent,CustomerShoppingMemory
from app.services.customer_memory_service import CustomerMemoryService
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
async def test_revoke_then_reenable_does_not_authorize_old_inflight_extraction(memory_db):
    sessions,(uid,_)=memory_db;started=asyncio.Event();resume=asyncio.Event()
    async def extract(text):
        started.set();await resume.wait()
        return {'category':'color','value':'blue','evidence':'I prefer blue'}
    async with sessions() as db:await CustomerMemoryService(db).set_consent(uid,True)
    async with sessions() as db:
        task=asyncio.create_task(CustomerMemoryService(db).collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=extract)))
        await started.wait()
        async with sessions() as writer:
            await CustomerMemoryService(writer).set_consent(uid,False)
            await CustomerMemoryService(writer).set_consent(uid,True)
        resume.set();assert not await task
    async with sessions() as db:
        service=CustomerMemoryService(db)
        assert await service.recall(uid)==[]
        assert await service.collect(uid,'I prefer blue',SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'})))
        assert await service.recall(uid)==['Customer explicitly prefers color: blue']

@pytest.mark.asyncio
@pytest.mark.parametrize('change',['disabled','policy'])
async def test_recall_rechecks_canonical_consent_in_same_fact_query(memory_db,change):
    sessions,(uid,_)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True);assert await service.collect(uid,'I prefer blue',llm)
    async with sessions() as db:
        service=CustomerMemoryService(db)
        async def precheck(user_id):
            async with sessions() as writer:
                await writer.execute(update(CustomerMemoryConsent).where(CustomerMemoryConsent.user_id==uid).values(**({'enabled':False} if change=='disabled' else {'policy_version':'old-policy'})))
                await writer.commit()
            return True
        service.enabled=precheck
        assert await service.recall(uid)==[]
