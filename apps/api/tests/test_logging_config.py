import json
import logging
import sys
import pytest
from app.core.logging_config import JsonFormatter, setup_logging


def record(message='event',args=(),exc_info=None):
    return logging.LogRecord('test.app',logging.INFO,'test.py',1,message,args,exc_info)


def test_real_json_unicode_and_allowlisted_context():
    r=record('hello %s',('world',));r.correlation_id='req_123';r.private_payload={'secret':'hide'}
    row=json.loads(JsonFormatter().format(r))
    assert row['message']=='hello world' and row['correlation_id']=='req_123'
    assert 'private_payload' not in row and row['level']=='INFO'


@pytest.mark.parametrize('text',[False,True])
def test_known_secrets_bearer_labels_urls_and_exceptions_are_redacted(text):
    try:raise ValueError('raw-private-payload')
    except ValueError:info=sys.exc_info()
    r=record('known-value Bearer abcxyz password=hidden api_key="hidden-key" redis://user:pass@host',exc_info=info)
    out=JsonFormatter(secret_values=['known-value'],text=text).format(r)
    for value in ('known-value','abcxyz','hidden-key','raw-private-payload','user:pass','password=hidden'):
        assert value not in out
    assert 'ValueError' in out
    if not text:assert json.loads(out)['exc_info']=={'type':'ValueError'}


def test_setup_is_idempotent_and_text_option_survives():
    root=logging.getLogger();old=list(root.handlers);level=root.level
    try:
        setup_logging(log_format='text');setup_logging(log_format='text')
        assert len(root.handlers)==1
        assert root.handlers[0].formatter.text is True
        setup_logging();assert root.handlers[0].formatter.text is False
    finally:root.handlers=old;root.setLevel(level)


def test_main_public_entrypoint_uses_setup(monkeypatch):
    import app.main as main
    import app.core.logging_config as config
    calls=[];monkeypatch.setattr(config,'setup_logging',lambda **kw:calls.append(kw))
    main.configure_logging()
    assert calls[0]['log_format']=='json' and calls[0]['level']=='INFO'
    assert calls[0]['secret_values']


def test_unknown_format_fails():
    with pytest.raises(ValueError):setup_logging(log_format='bad')
