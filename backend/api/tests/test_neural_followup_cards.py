"""Two-turn flow: a follow-up like 'which has better battery?' must be answered about the cards the customer was just shown, not a fresh search. Before this, SessionMemory kept only text and the brief, so each turn searched again."""
import json
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from app.schemas.ai_actions import NeuralCoreResponse
from app.services.neural_core_service import NeuralCoreService, RouterDecision, SearchTarget, SessionMemory
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row


def _svc(memory, decision):
    svc = NeuralCoreService(object(), object())
    svc.is_healthy = True
    svc.configuration_error = False
    svc._hydrate_session = AsyncMock(return_value=memory)
    svc._persist_session = AsyncMock()
    svc._analyze_intent = AsyncMock(return_value=decision)
    return svc


def _cards():
    return [catalog_result(row(id=1, name='Studio Headphones', price=Decimal('79.00'))), catalog_result(row(id=2, name='Earbuds Mini', price=Decimal('49.00')))]


def _resp(cards):
    return NeuralCoreResponse(text='Shown', response_kind='catalog_results', explain='x', confidence=0.5, products=cards, telemetry={'intent': 'PRODUCT_SEARCH', 'entities': [], 'turn': 0})


@pytest.mark.asyncio
async def test_catalog_turn_remembers_the_cards_it_showed():
    memory = SessionMemory(user_name='C')
    svc = _svc(memory, RouterDecision(intent='PRODUCT_SEARCH', search_subject='headphones', query='headphones', shopping_task='search'))
    svc._handle_product_search = AsyncMock(return_value=_resp(_cards()))
    await svc._handle_message_with_context(object(), 'headphones', None, 's')
    assert memory.last_card_ids == [1, 2] and memory.last_card_names == ['Studio Headphones', 'Earbuds Mini']


@pytest.mark.asyncio
async def test_followup_about_these_reuses_the_last_cards_and_skips_search():
    memory = SessionMemory(user_name='C', last_card_ids=[1, 2], last_card_names=['Studio Headphones', 'Earbuds Mini'])
    svc = _svc(memory, RouterDecision(intent='PRODUCT_SEARCH', search_subject='battery', query='battery', shopping_task='comparison'))
    svc._handle_product_search = AsyncMock(side_effect=AssertionError('fresh search must not run'))
    svc._catalog_response = AsyncMock(return_value=_resp(_cards()))
    svc._recheck_catalog_response = AsyncMock()
    await svc._handle_message_with_context(object(), 'Which of these has better battery?', None, 's')
    args = svc._catalog_response.await_args
    assert [p.id for p in args.args[1]] == [1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize('message,targets,task', [
    ('Which one is the best laptop under $500?', [SearchTarget(product_name='laptop')], 'consultation'),  # names a new product
    ('Which of these has better battery?', [], 'search'),  # not an informational task
])
async def test_fresh_requests_still_search(message, targets, task):
    memory = SessionMemory(user_name='C', last_card_ids=[1, 2], last_card_names=['Studio Headphones', 'Earbuds Mini'])
    svc = _svc(memory, RouterDecision(intent='PRODUCT_SEARCH', search_subject='x', query='x', shopping_task=task, targets=targets))
    svc._handle_product_search = AsyncMock(return_value=_resp(_cards()))
    svc._handle_staged_product_search = AsyncMock(return_value=_resp(_cards()))
    svc._handle_scoped_target_search = AsyncMock(return_value=_resp(_cards()))
    svc._catalog_response = AsyncMock(side_effect=AssertionError('follow-up path must not run'))
    await svc._handle_message_with_context(object(), message, None, 's')


def test_old_sessions_without_card_memory_still_load():
    memory = SessionMemory.model_validate({'user_name': 'C', 'history': []})
    assert memory.last_card_ids == [] and memory.last_card_names == []
