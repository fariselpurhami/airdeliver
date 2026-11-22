"""Assert full structured LogRecord fields, not just formatted log text."""
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.services.neural_core_service import NeuralCoreService,SessionMemory,RouterDecision
from tests.test_nlu_behavior_contracts import service as nlu_service


def assert_private_absent(caplog):
    serialized=json.dumps([vars(r) for r in caplog.records],default=str)
    assert 'PRIVATE_MARKER' not in serialized
    assert all(r.exc_info is None for r in caplog.records)


@pytest.mark.asyncio
async def test_support_failure_logs_never_include_raw_session_query_provider_or_image(caplog):
    caplog.set_level(logging.INFO)
    cache=SimpleNamespace(set_json=AsyncMock(side_effect=RuntimeError('PRIVATE_MARKER_PROVIDER')))
    engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(side_effect=RuntimeError('PRIVATE_MARKER_SEARCH')),
                           search_by_image_vector=AsyncMock(side_effect=RuntimeError('PRIVATE_MARKER_IMAGE')))
    svc=NeuralCoreService(engine,cache)
    await svc._persist_session('PRIVATE_MARKER_SESSION',SessionMemory(user_name='PRIVATE_MARKER_NAME'))
    await svc._handle_product_search(None,'PRIVATE_MARKER_QUERY')
    await svc._handle_visual_search('PRIVATE_MARKER_BASE64')
    assert_private_absent(caplog)


@pytest.mark.asyncio
async def test_support_success_route_does_not_log_name_or_session(caplog):
    caplog.set_level(logging.INFO)
    svc=NeuralCoreService(object(),object())
    svc._hydrate_session=AsyncMock(return_value=SessionMemory(user_name='PRIVATE_MARKER_NAME'))
    svc._persist_session=AsyncMock()
    svc._analyze_intent=AsyncMock(return_value=RouterDecision(intent='SOCIAL_CHAT',social_reply='Shopping help'))
    await svc.handle_message(None,'PRIVATE_MARKER_QUERY',None,'PRIVATE_MARKER_SESSION')
    assert_private_absent(caplog)


@pytest.mark.asyncio
async def test_extracted_customer_fact_and_provider_error_are_not_log_fields(caplog):
    caplog.set_level(logging.INFO)
    svc=nlu_service()
    svc.llm_service.extract_memory_worthy_facts=AsyncMock(return_value='PRIVATE_MARKER_FACT')
    svc.search_engine.remember_user_fact=AsyncMock(side_effect=RuntimeError('PRIVATE_MARKER_PROVIDER'))
    await svc._bg_memorize(7,'PRIVATE_MARKER_CUSTOMER preference')
    assert_private_absent(caplog)
