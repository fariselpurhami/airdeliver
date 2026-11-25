import json
import logging
import pytest
from app.core.logging_config import JsonFormatter
from app.services.ai_nlu_service import StructuredLog
import app.services.ai_nlu_service as commerce


@pytest.fixture(autouse=True)
def isolated_logger(monkeypatch,caplog):
    logger=logging.Logger("test.commerce",logging.DEBUG)
    logger.addHandler(caplog.handler)
    monkeypatch.setattr(commerce,"logger",logger)


@pytest.mark.parametrize('text',[False,True])
def test_current_structured_diagnostics_drop_private_prose_before_formatter(caplog,text):
    with caplog.at_level(logging.INFO,logger='airdeliver.commerce_os'):
        StructuredLog.info('matrix_stage_failed',user_id=7,stage='fetch_personal',error_type='TimeoutError',elapsed_ms=12,
            input='PRIVATE_CUSTOMER',query='PRIVATE_QUERY',raw_preview='PRIVATE_MODEL',
            error='PRIVATE_PROVIDER',key='PRIVATE_CACHE_KEY',reason='PRIVATE_PROSE',
            signal=['PRIVATE_TERMS'],price_max=1000,product='PRIVATE_NAME')
    record=caplog.records[-1]
    # Not merely dropped by final formatter: private data never enters LogRecord.
    assert 'PRIVATE_' not in str(record.__dict__)
    rendered=JsonFormatter(text=text).format(record)
    assert 'fetch_personal' in rendered and 'TimeoutError' in rendered and '12' in rendered
    assert 'PRIVATE_' not in rendered and '1000' not in rendered


def test_unbounded_or_nonfinite_metadata_cannot_smuggle_payload(caplog):
    with caplog.at_level(logging.INFO,logger='airdeliver.commerce_os'):
        StructuredLog.info('event with PRIVATE_BODY',stage='PRIVATE prose with spaces',error_type='bad\nbody',user_id=True,elapsed_ms=float('inf'))
    record=caplog.records[-1]
    assert record.getMessage()=='commerce_diagnostic | {}'


def test_exception_body_never_reaches_record(caplog):
    try:
        raise RuntimeError('PRIVATE_EXCEPTION')
    except RuntimeError:
        StructuredLog.exception('operation_failed')
    record=caplog.records[-1]
    assert record.exc_info is None
    assert 'PRIVATE_EXCEPTION' not in str(record.__dict__)
    assert 'RuntimeError' in record.getMessage()
