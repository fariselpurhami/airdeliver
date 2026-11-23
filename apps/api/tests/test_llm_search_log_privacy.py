import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.free_llm_service import FreeLLMService
import app.services.free_llm_service as module
from app.core.logging_config import JsonFormatter


@pytest.fixture
def service(monkeypatch,caplog):
    monkeypatch.setattr(FreeLLMService,'_instance',None)
    value=FreeLLMService()
    logger=logging.Logger('test.llm',logging.DEBUG)
    logger.addHandler(caplog.handler)
    monkeypatch.setattr(module,'logger',logger)
    return value


@pytest.mark.asyncio
async def test_short_search_fallback_preserved_without_raw_input_log(service,monkeypatch,caplog):
    monkeypatch.setattr(service,'_chat_completion',AsyncMock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=''))])))
    result=await service.extract_search_terms('PRIVATE_CUSTOMER_QUERY')
    assert result=='PRIVATE_CUSTOMER_QUERY'
    records=[r for r in caplog.records if 'short_result' in r.getMessage()]
    assert len(records)==1 and 'input_chars=' in records[0].getMessage()
    assert 'PRIVATE_' not in str(records[0].__dict__)


@pytest.mark.asyncio
async def test_orchestration_keeps_search_terms_in_response_not_logs(service,monkeypatch,caplog):
    strategy=SimpleNamespace(is_direct_product_request=True,response_tone='neutral',
        direct_answer_prefix='',model_dump=lambda:{'is_direct_product_request':True})
    monkeypatch.setattr(service,'strategize_search',AsyncMock(return_value=strategy))
    monkeypatch.setattr(service,'extract_search_terms',AsyncMock(return_value='PRIVATE_MODEL_TERMS'))
    monkeypatch.setattr(service,'filter_and_recommend',AsyncMock(return_value=None))
    response=await service.handle_commerce_interaction('PRIVATE_CUSTOMER_QUERY',[])
    assert response['search_terms']=='PRIVATE_MODEL_TERMS'
    records=[r for r in caplog.records if 'commerce.orchestrator' in r.getMessage()]
    assert len(records)==1 and 'product_count=0' in records[0].getMessage()
    for record in records:
        assert 'PRIVATE_' not in str(record.__dict__)
        assert 'PRIVATE_' not in JsonFormatter().format(record)
