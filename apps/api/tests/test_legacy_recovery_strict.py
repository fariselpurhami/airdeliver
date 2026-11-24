"""Legacy read-only recovery/copy caller migration, not voice/cart mutation."""
import asyncio,logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService
from tests.test_llm_execution_limits import service,completion
from tests.test_nlu_behavior_contracts import service as nlu

@pytest.mark.asyncio
async def test_smart_recovery_actual_strict_transport_success_dedup_and_failure(caplog):
    llm=service();svc=nlu();svc.llm_service=llm
    rows=[{'id':1,'name':'chair'},{'id':2,'name':'desk'}]
    svc.search_engine.perform_hybrid_search_pure=AsyncMock(return_value=rows)
    llm._chat_completion=AsyncMock(return_value=completion('Furniture | chair desk'))
    result=await svc._perform_smart_recovery('office furniture')
    assert [p['id'] for p in result]==[1,2]
    assert svc.search_engine.perform_hybrid_search_pure.await_count==2
    llm._chat_completion=AsyncMock(side_effect=ConnectionError('private failure sentinel'))
    svc.search_engine.perform_hybrid_search_pure.reset_mock()
    with caplog.at_level(logging.ERROR):result=await svc._perform_smart_recovery('private customer sentinel furniture')
    assert result==rows
    assert svc.search_engine.perform_hybrid_search_pure.await_count==1
    assert 'private failure sentinel' not in caplog.text and 'private customer sentinel' not in caplog.text
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    svc.search_engine.perform_hybrid_search_pure.reset_mock()
    with pytest.raises(asyncio.CancelledError):await svc._perform_smart_recovery('chair')
    svc.search_engine.perform_hybrid_search_pure.assert_not_awaited()

@pytest.mark.asyncio
async def test_genius_strict_success_failure_blank_and_cancel(caplog):
    svc=nlu();llm=service();svc.llm_service=llm
    svc._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='EXPLORER',tier='MEDIUM'))
    product={'id':1,'name':'chair','price':20}
    llm._chat_completion=AsyncMock(return_value=completion('Listed chair facts'))
    assert await svc._generate_genius_response(7,'chair',product)=='Listed chair facts'
    for failure in [ConnectionError('private failure sentinel'),None]:
        llm._chat_completion=AsyncMock(side_effect=failure) if failure else AsyncMock(return_value=completion(''))
        with caplog.at_level(logging.ERROR):result=await svc._generate_genius_response(7,'private customer sentinel',product)
        assert 'could not assess' in result and 'Listed price: 20' in result
        assert 'private failure sentinel' not in caplog.text and 'private customer sentinel' not in caplog.text
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):await svc._generate_genius_response(7,'chair',product)

@pytest.mark.asyncio
async def test_older_injected_recovery_adapter_remains_supported():
    svc=nlu();svc.llm_service=SimpleNamespace(generate_response=AsyncMock(return_value='Furniture | chair desk'))
    svc.search_engine.perform_hybrid_search_pure=AsyncMock(return_value=[])
    assert await svc._perform_smart_recovery('chair')==[]
    svc.llm_service.generate_response.assert_awaited_once()
