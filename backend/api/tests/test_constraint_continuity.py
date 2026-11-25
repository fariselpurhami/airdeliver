import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.constraint_continuity import replacement_is_explicit
from app.services.neural_core_service import NeuralCoreService,RouterDecision,SessionMemory
from app.services.shopping_discovery import ShoppingBrief

@pytest.mark.asyncio
async def test_reset_requires_literal_current_span_and_review():
    infer=AsyncMock(return_value=json.dumps({'explicit_replacement':True}))
    assert not await replacement_is_explicit(infer,'add blue','forget old constraints')
    infer.assert_not_awaited()
    assert await replacement_is_explicit(infer,'forget old constraints, use blue','forget old constraints')
    infer.return_value=json.dumps({'explicit_replacement':False})
    assert not await replacement_is_explicit(infer,'also blue','also blue')

@pytest.mark.asyncio
@pytest.mark.parametrize('replace',[False,True])
async def test_successive_turn_preserves_prior_hard_features_unless_explicit_replacement(replace):
    svc=NeuralCoreService(object(),object());svc.is_healthy=True;svc.configuration_error=False
    memory=SessionMemory(user_name='Client',shopping_brief=ShoppingBrief(required_features=['16GB RAM'],excluded_terms=['red']))
    memory.append_turn('laptop16GB RAM, no red','Which other features?')
    svc._hydrate_session=AsyncMock(return_value=memory);svc._persist_session=AsyncMock()
    decision=RouterDecision(intent='PRODUCT_SEARCH',search_subject='laptop',query='laptop',brief=ShoppingBrief(required_features=['SSD']),constraint_replacement_signal='replace old requirements' if replace else None)
    svc._analyze_intent=AsyncMock(return_value=decision)
    svc._handle_product_search=AsyncMock(return_value=__import__('app.schemas.ai_actions',fromlist=['NeuralCoreResponse']).NeuralCoreResponse(text='Result',response_kind='text',confidence=0,explain='test',telemetry={'intent':'PRODUCT_SEARCH'}))
    await svc._handle_message_with_context(object(),'laptop SSD',None,'session')
    brief=svc._handle_product_search.await_args.args[2]
    assert brief.required_features==(['SSD'] if replace else ['16GB RAM','SSD'])
    assert brief.excluded_terms==([] if replace else ['red'])
