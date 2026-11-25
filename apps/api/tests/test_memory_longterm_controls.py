"""Owner-approved lifecycle changes at real PostgreSQL boundaries."""
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select,update
from app.models.customer_memory import CustomerMemoryConsent,CustomerShoppingMemory
from app.services.customer_memory_service import CustomerMemoryService,LONG_TERM_EXPIRY
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
async def test_learning_off_preserves_longterm_recall_until_separate_erase(memory_db):
    sessions,(uid,other)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db)
        await service.set_consent(uid,True)
        assert await service.collect(uid,'I prefer blue',llm)
        await service.set_consent(uid,False)
        assert not await service.collect(uid,'I prefer blue',llm)
        assert llm.extract_shopping_preferences.await_count==1
        assert len(await service.recall(uid))==1
        assert await service.recall(other)==[]
        exported=await service.export(uid)
        assert exported['retention_days'] is None and not exported['enabled']
        assert datetime.fromisoformat(exported['preferences'][0]['expires_at'])==LONG_TERM_EXPIRY
        await service.erase_preferences(other)
        assert len(await service.recall(uid))==1
        await service.erase_preferences(uid)
        assert await service.recall(uid)==[]
        assert not (await service.export(uid))['preferences']

@pytest.mark.asyncio
async def test_old_policy_not_silently_enrolled_or_extended_until_explicit_enable(memory_db):
    sessions,(uid,_)=memory_db
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    async with sessions() as db:
        service=CustomerMemoryService(db)
        await service.set_consent(uid,True)
        assert await service.collect(uid,'I prefer blue',llm)
        old_expiry=datetime.now(timezone.utc)+timedelta(days=12)
        await db.execute(update(CustomerMemoryConsent).where(CustomerMemoryConsent.user_id==uid).values(policy_version='shopping-v1'))
        await db.execute(update(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==uid).values(expires_at=old_expiry))
        await db.commit()
        assert not await service.enabled(uid)
        assert not await service.collect(uid,'I prefer blue',llm)
        assert len(await service.recall(uid))==1
        assert not (await service.export(uid))['enabled']
        await service.set_consent(uid,True)
        rows=(await db.execute(select(CustomerShoppingMemory).where(CustomerShoppingMemory.user_id==uid))).scalars().all()
        assert rows[0].expires_at==LONG_TERM_EXPIRY
