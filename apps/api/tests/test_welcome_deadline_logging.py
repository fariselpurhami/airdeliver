"""Scheduling and transport faults only, no real model/provider calls."""
import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService, MatrixConfig
from app.services.ai_commerce_engine import AICommerceEngine, EngineLimits, SearchFilter, PRODUCT_TEXT_MODEL
from app.services.neural_core_service import _log_inference_failure
from app.core.logging_config import JsonFormatter

@pytest.mark.asyncio
async def test_matrix_deadline_reports_real_failure_and_cancels_pending_work(caplog):
    service=object.__new__(AINLUService)
    service.config=MatrixConfig(matrix_timeout_sec=.02,matrix_stage_timeout_sec=.01)
    cancelled=asyncio.Event()
    async def blocked(user):
        try: await asyncio.Event().wait()
        finally: cancelled.set()
    service._handle_initial_suggestions_bounded=blocked
    service.ui=SimpleNamespace(publish=AsyncMock())
    with caplog.at_level(logging.INFO): await service._handle_initial_suggestions(1)
    assert cancelled.is_set()
    assert service.ui.publish.await_args.args[1]['type']=='error'
    assert 'matrix_generation_failed' in caplog.text and 'TimeoutError' in caplog.text
    assert 'matrix_generation_completed' not in caplog.text

@pytest.mark.asyncio
async def test_matrix_stage_breadcrumbs_and_cancellation_are_not_silent(caplog):
    service=object.__new__(AINLUService);service.config=MatrixConfig(matrix_stage_timeout_sec=.01)
    with caplog.at_level(logging.INFO):
        assert await service._matrix_stage(1,'fetch_personal',AsyncMock(return_value=[]))==[]
        with pytest.raises(TimeoutError):
            await service._matrix_stage(1,'fetch_trending',lambda: asyncio.Event().wait())
    assert 'matrix_stage_completed' in caplog.text and 'matrix_stage_failed' in caplog.text
    assert 'fetch_trending' in caplog.text

@pytest.mark.asyncio
async def test_milvus_semaphore_wait_is_included_in_deadline():
    engine=object.__new__(AICommerceEngine)
    engine.limits=EngineLimits(vector_search_timeout_seconds=.02)
    engine._vector_search_semaphore=asyncio.Semaphore(0)
    engine.milvus_client=SimpleNamespace(search=lambda **kw: pytest.fail('must not submit blocked work'))
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(engine._search_milvus_text([0.]*PRODUCT_TEXT_MODEL.dimension,5,SearchFilter()),.2)

@pytest.mark.parametrize('text',[False,True])
def test_router_diagnostics_survive_formatter_without_private_error_body(text):
    exc=RuntimeError('PRIVATE_PROVIDER_BODY api_key=secret')
    exc.status_code=401
    class Capture(logging.Handler):
        def emit(self,record): self.result=JsonFormatter(text=text).format(record)
    logger=logging.getLogger('airdeliver.neural_core');handler=Capture();logger.addHandler(handler)
    try: _log_inference_failure('neural_core.router.inference_failure',exc)
    finally: logger.removeHandler(handler)
    assert 'RuntimeError' in handler.result and '401' in handler.result and 'authentication' in handler.result
    assert 'PRIVATE' not in handler.result and 'secret' not in handler.result

@pytest.mark.asyncio
async def test_matrix_ui_failure_is_not_reported_as_stream_success(caplog):
    service=object.__new__(AINLUService)
    service.config=MatrixConfig(stream_delay_sec=0)
    service.ui=SimpleNamespace(publish=AsyncMock(side_effect=ConnectionError('private transport detail')))
    with caplog.at_level(logging.INFO), pytest.raises(ConnectionError):
        await service._stream_row(1,'Selection','product_carousel',[], 'Reason')
    assert 'stream_row_transport_failure' in caplog.text

@pytest.mark.asyncio
async def test_cart_add_timings_surround_actual_persistence_and_confirmation(caplog):
    from app.services.ai_cart_service import AICartService
    from tests.test_ai_cart_service import FakeDB, FakeCache, make_product
    cache=FakeCache()
    broker=SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True)))
    with caplog.at_level(logging.INFO):
        await AICartService(FakeDB(make_product()),cache,broker).handle_add_to_cart({'user_id':1,'product_id':7})
    assert cache._cart['items'][0]['quantity']==1
    for stage in ('catalog_read','cart_read','cart_persist','operation'):
        assert f'cart_add_stage_completed stage={stage}' in caplog.text
