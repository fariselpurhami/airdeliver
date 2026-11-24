# Historical retained-method contracts. New production bridge is tested separately.
"""Pin NLU's behavior/memory/public embedding contracts."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.ai_commerce_engine import AICommerceEngine
from app.services.ai_meta_cognition import MetaCognitionService
from app.services.ai_nlu_service import AINLUService, RedisKeys


def service():
    return AINLUService(db=object(), search_engine=SimpleNamespace(), rabbitmq=object(),
                       cache=SimpleNamespace(), llm_service=SimpleNamespace(), behavior_engine=None)


def test_nlu_and_behavior_use_same_ghost_key():
    assert RedisKeys.ghost_profile(7) == BehaviorEngine._key_ghost(7)


@pytest.mark.asyncio
async def test_public_embedding_contract_delegates():
    engine = object.__new__(AICommerceEngine)
    engine._get_query_embedding = AsyncMock(return_value=[1., 0.])
    assert await engine.get_query_embedding("headphones") == [1., 0.]
    engine._get_query_embedding.assert_awaited_once_with("headphones")


@pytest.mark.asyncio
async def test_background_memory_never_uses_legacy_unconsented_fact_hook():
    svc = service()
    captured = []
    async def remember_user_fact(user_id, fact_text):
        captured.append((user_id, fact_text))
    svc.llm_service.extract_memory_worthy_facts = AsyncMock(return_value="prefers red shoes")
    svc.search_engine.remember_user_fact = remember_user_fact
    await svc._bg_memorize(7, "I prefer red shoes")
    assert captured == []
    svc.llm_service.extract_memory_worthy_facts.assert_not_awaited()


@pytest.mark.asyncio
async def test_genius_response_accepts_real_typed_cognitive_assessment():
    svc = service()
    svc._get_user_dna = AsyncMock(return_value=SimpleNamespace(persona="EXPLORER", tier="MEDIUM"))
    svc.cache.get_json = AsyncMock(return_value={"pos": [1., 0.], "confidence": .8})
    svc.search_engine.get_query_embedding = AsyncMock(return_value=[1., 0.])
    svc.meta_cognition = MetaCognitionService()
    svc.llm_service.generate_response = AsyncMock(return_value="Verified headphones information")
    result = await svc._generate_genius_response_legacy_unreviewed(7, "headphones", {"id": 1, "name": "headphones", "price": 20})
    assert result == "Verified headphones information"
    svc.llm_service.generate_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_unavailable_meta_does_not_invent_confidence_or_duplicate_embedding():
    svc=service()
    svc._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona="EXPLORER",tier="MEDIUM"))
    svc.search_engine.get_query_embedding=AsyncMock(side_effect=RuntimeError("must not allocate inference"))
    svc.llm_service.generate_response=AsyncMock(return_value="Listed item facts")
    await svc._generate_genius_response_legacy_unreviewed(7,"headphones",{"id":1,"name":"headphones","price":20})
    svc.search_engine.get_query_embedding.assert_not_awaited()
    prompt=svc.llm_service.generate_response.call_args.kwargs['system_role']
    assert 'No calibrated confidence or learned preference estimate is available' in prompt
    assert 'Never treat a recommendation as transaction approval' in prompt


@pytest.mark.asyncio
async def test_generation_failure_does_not_invent_product_fit():
    svc=service()
    svc._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona="EXPLORER",tier="MEDIUM"))
    svc.llm_service.generate_response=AsyncMock(side_effect=RuntimeError("unavailable"))
    result=await svc._generate_genius_response_legacy_unreviewed(7,"headphones",{"id":1,"name":"headphones","price":20})
    assert 'matches your needs' not in result
    assert 'could not assess' in result
