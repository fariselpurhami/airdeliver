import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from scripts.diagnose_groq_route import ThirdLedger, diagnose_once
from scripts.reconcile_groq_acceptance import Successor
from scripts.accept_dev_cart import APPROVAL, AcceptanceStopped


def prior_ledgers(tmp_path):
    first=tmp_path/'v1.json'; second=tmp_path/'v2.json'
    first.write_text(json.dumps({'approval':APPROVAL,'calls_reserved':1,'events':[
        {'leg':'groq','case':1,'stopped_error':'NotFoundError','calls_reserved':1},
        {'test_user_deactivated':True}]}))
    ledger=Successor(first,second);ledger.reserve()
    ledger.record({'leg':'models_list','stopped':True,'http_status':404,'calls_reserved_total':2});ledger.close()
    return first,second


@pytest.mark.asyncio
async def test_third_request_inherits_two_and_refuses_repetition(tmp_path):
    first,second=prior_ledgers(tmp_path);before=[p.read_bytes() for p in (first,second)]
    destination=tmp_path/'v3.json';ledger=ThirdLedger(first,second,destination)
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=SimpleNamespace(data=[]))))
    try:
        await diagnose_once(ledger,client)
        assert ledger.state['calls_reserved_total']==3
        assert ledger.state['events'][-1]['requests_remaining']==5
        assert [p.read_bytes() for p in (first,second)]==before
        with pytest.raises(AcceptanceStopped):await diagnose_once(ledger,client)
        assert client.models.list.call_count==1
    finally:ledger.close()
    with pytest.raises(FileExistsError):ThirdLedger(first,second,destination)


@pytest.mark.asyncio
async def test_third_failure_retains_usage_without_raw_body(tmp_path,capsys):
    first,second=prior_ledgers(tmp_path);ledger=ThirdLedger(first,second,tmp_path/'v3.json')
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(side_effect=RuntimeError('secret raw body'))))
    try:
        await diagnose_once(ledger,client)
        assert ledger.state['calls_reserved_total']==3
        assert ledger.state['events'][-1]['stopped'] is True
        assert 'secret raw body' not in capsys.readouterr().out
    finally:ledger.close()


def test_changed_source_or_wrong_total_cannot_create_successor(tmp_path):
    first,second=prior_ledgers(tmp_path)
    row=json.loads(second.read_text());row['calls_reserved_total']=1;second.write_text(json.dumps(row))
    with pytest.raises(AcceptanceStopped):ThirdLedger(first,second,tmp_path/'v3.json')
    assert not (tmp_path/'v3.json').exists()
