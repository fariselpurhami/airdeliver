import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,PRODUCT_VISION_MODEL
from app.services.ai_nlu_service import AINLUService,RequestContext
from app.services.neural_core_service import NeuralCoreService

@pytest.mark.asyncio
@pytest.mark.parametrize('bad',[float('nan'),float('inf'),True])
async def test_invalid_direct_visual_vector_never_reaches_native_search(bad):
    engine=AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object())
    engine.bootstrap=AsyncMock();engine._run_vector_native=AsyncMock()
    assert await engine.search_by_image_vector([bad]*PRODUCT_VISION_MODEL.dimension)==[]
    engine._run_vector_native.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('hint',[None,{},'generic product','x'*257,'bad\nhint','https://invalid.test'])
async def test_original_vision_failure_keeps_caption_not_invented_trends(hint):
    llm=SimpleNamespace(analyze_product_image=AsyncMock(return_value=hint))
    svc=AINLUService(object(),object(),object(),object(),llm)
    request=svc._parse_incoming_message({'user_id':17,'message':'find this chair','image_base64':'image'})
    request=replace(request,image_b64='image')
    assert await svc._resolve_vision_query(request,RequestContext(17,'test',0))==('find this chair','')

@pytest.mark.asyncio
@pytest.mark.parametrize('hint',['invented model','x'*257,'desk\nchair','https://invalid.test'])
async def test_original_optimizer_cannot_invent_or_overrun(monkeypatch,hint):
    import app.services.ai_nlu_service as module
    monkeypatch.setattr(module,'_strict_model_text',AsyncMock(return_value=hint))
    svc=AINLUService(object(),object(),object(),object(),SimpleNamespace())
    question='please find the desk and chair'
    assert await svc._optimize_search_query(question)==question

@pytest.mark.asyncio
async def test_current_visual_cancellation_never_publishes():
    svc=NeuralCoreService(SimpleNamespace(search_by_image_vector=AsyncMock(side_effect=asyncio.CancelledError())),object())
    svc._catalog_response=AsyncMock()
    with pytest.raises(asyncio.CancelledError):await svc._handle_visual_search('image')
    svc._catalog_response.assert_not_awaited()

@pytest.mark.asyncio
async def test_visual_turn_deadline_returns_no_cards():
    svc=NeuralCoreService(object(),object())
    svc._handle_visual_search_bounded=AsyncMock(side_effect=TimeoutError())
    response=await svc._handle_visual_search('image')
    assert response.products==[] and response.response_kind=='system_notice'

@pytest.mark.asyncio
async def test_original_vision_transport_outage_does_not_create_fallback_category():
    svc=AINLUService(object(),object(),object(),object(),SimpleNamespace(analyze_product_image=AsyncMock(side_effect=TimeoutError())))
    request=replace(svc._parse_incoming_message({'user_id':17,'message':'caption'}),image_b64='image')
    assert await svc._resolve_vision_query(request,RequestContext(17,'test',0))==('caption','')
