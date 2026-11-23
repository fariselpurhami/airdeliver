import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from scripts.reconcile_groq_acceptance import Successor, list_once, error_metadata
from scripts.accept_dev_cart import APPROVAL, AcceptanceStopped


def original(tmp_path):
    path = tmp_path / 'source.json'
    path.write_text(json.dumps({'approval': APPROVAL, 'calls_reserved': 1, 'events':[
        {'leg':'groq','case':1,'stopped_error':'NotFoundError','calls_reserved':1},
        {'test_user_deactivated': True}]}))
    return path


@pytest.mark.asyncio
async def test_one_list_carries_budget_and_keeps_original_unchanged(tmp_path):
    source=original(tmp_path); before=source.read_bytes()
    successor=Successor(source,tmp_path/'v2.json')
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=SimpleNamespace(data=[
        SimpleNamespace(id='openai/gpt-oss-20b',active=True),
        SimpleNamespace(id='malicious model text with spaces',active=True),
        SimpleNamespace(id='inactive',active=False)]))))
    try:
        await list_once(successor,client)
        assert successor.state['calls_reserved_total']==2
        assert successor.state['source_sha256']==hashlib.sha256(before).hexdigest()
        assert successor.state['events'][-1]['requests_remaining']==6
        assert successor.state['events'][-1]['active_model_ids']==['openai/gpt-oss-20b']
        assert source.read_bytes()==before
        with pytest.raises(AcceptanceStopped):await list_once(successor,client)
        assert client.models.list.call_count==1
    finally: successor.close()
    with pytest.raises(FileExistsError): Successor(source,tmp_path/'v2.json')


@pytest.mark.parametrize('calls',[0,2,8,True])
def test_different_original_usage_cannot_reset_budget(tmp_path,calls):
    source=original(tmp_path);data=json.loads(source.read_text());data['calls_reserved']=calls
    source.write_text(json.dumps(data))
    with pytest.raises(AcceptanceStopped):Successor(source,tmp_path/'v2.json')
    assert not (tmp_path/'v2.json').exists()


@pytest.mark.asyncio
async def test_failure_counts_and_prints_no_raw_body(tmp_path,capsys):
    source=original(tmp_path);ledger=Successor(source,tmp_path/'v2.json')
    error=RuntimeError('private raw body must stay hidden')
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(side_effect=error)))
    try:
        await list_once(ledger,client)
        assert ledger.state['calls_reserved_total']==2
        assert ledger.state['events'][-1]['stopped'] is True
        assert 'private raw body' not in capsys.readouterr().out
    finally:ledger.close()


def test_error_code_is_allowlisted_not_echoed():
    assert error_metadata(SimpleNamespace(code='secret value',status_code=404))['provider_code']=='not_in_allowlist'
    assert error_metadata(SimpleNamespace(code='model_not_found',status_code=404))['provider_code']=='model_not_found'
