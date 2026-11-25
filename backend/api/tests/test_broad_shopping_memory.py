"""Broader memory remains owner-stated, finite, canonical and non-sensitive."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.customer_memory_service import CustomerMemoryService,valid_candidate
from app.services.shopping_memory_policy import SHOPPING_VALUES
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.parametrize('category,value',[('fit','relaxed'),('pattern','striped'),('closure','zipper'),('comfort','breathable'),('packaging','recyclable packaging'),('shopping_priority','quality'),('delivery_preference','pickup')])
def test_expanded_finite_preference_categories(category,value):
    text='I prefer '+value
    assert valid_candidate(dict(category=category,value=value,evidence=text),text)==(category,value)

@pytest.mark.parametrize('text',['I do not think I prefer blue','My wife says I prefer blue','I prefer blue for my friend','They said I prefer blue'])
def test_selected_affirmative_fragment_cannot_launder_negated_or_third_party_claim(text):
    assert valid_candidate(dict(category='color',value='blue',evidence='I prefer blue'),text) is None

@pytest.mark.asyncio
async def test_multiple_preferences_collected_once_and_persist_across_sessions(memory_db):
    sessions,(uid,other)=memory_db
    text='I prefer relaxed. I like striped. My favorite is blue.'
    proposals=[dict(category='fit',value='relaxed',evidence='I prefer relaxed'),dict(category='pattern',value='striped',evidence='I like striped'),dict(category='color',value='blue',evidence='My favorite is blue')]
    extractor=SimpleNamespace(extract_shopping_preferences_batch=AsyncMock(return_value={'preferences':proposals}))
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        assert await service.collect(uid,text,extractor)
        assert await service.collect(uid,text,extractor)
    async with sessions() as db:
        service=CustomerMemoryService(db)
        assert len((await service.export(uid))['preferences'])==3
        assert await service.recall(other)==[]
        await service.set_consent(uid,False)
        assert len(await service.recall(uid))==3
        assert not await service.collect(uid,text,extractor)
        assert extractor.extract_shopping_preferences_batch.await_count==2

@pytest.mark.asyncio
async def test_old_v2_not_authority_for_broader_collection(memory_db):
    from sqlalchemy import update
    from app.models.customer_memory import CustomerMemoryConsent
    sessions,(uid,_)=memory_db
    extractor=SimpleNamespace(extract_shopping_preferences_batch=AsyncMock())
    async with sessions() as db:
        service=CustomerMemoryService(db);await service.set_consent(uid,True)
        await db.execute(update(CustomerMemoryConsent).where(CustomerMemoryConsent.user_id==uid).values(policy_version='shopping-v2'));await db.commit()
        assert not await service.collect(uid,'I prefer relaxed',extractor)
        extractor.extract_shopping_preferences_batch.assert_not_awaited()
