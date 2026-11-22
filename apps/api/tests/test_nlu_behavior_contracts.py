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
async def test_background_memory_uses_engine_fact_parameter():
    svc = service()
    captured = []
    async def remember_user_fact(user_id, fact_text):
        captured.append((user_id, fact_text))
    svc.llm_service.extract_memory_worthy_facts = AsyncMock(return_value="prefers red shoes")
    svc.search_engine.remember_user_fact = remember_user_fact
    await svc._bg_memorize(7, "I prefer red shoes")
    assert captured == [(7, "prefers red shoes")]


@pytest.mark.asyncio
async def test_genius_response_accepts_real_typed_cognitive_assessment():
    svc = service()
    svc._get_user_dna = AsyncMock(return_value=SimpleNamespace(persona="EXPLORER", tier="MEDIUM"))
    svc.cache.get_json = AsyncMock(return_value={"pos": [1., 0.], "confidence": .8})
    svc.search_engine.get_query_embedding = AsyncMock(return_value=[1., 0.])
    svc.meta_cognition = MetaCognitionService()
    svc.llm_service.generate_response = AsyncMock(return_value="Verified headphones information")
    result = await svc._generate_genius_response(7, "headphones", {"id": 1, "name": "headphones", "price": 20})
    assert result == "Verified headphones information"
    svc.llm_service.generate_response.assert_awaited_once()
