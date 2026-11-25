import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from tests.test_third_groq_diagnostic import prior_ledgers
from scripts.diagnose_groq_route import ThirdLedger
from scripts.verify_corrected_groq_route import FourthLedger,list_once
from scripts.accept_dev_cart import AcceptanceStopped


def chain(tmp_path):
    first,second=prior_ledgers(tmp_path);third=tmp_path/'v3.json'
    ledger=ThirdLedger(first,second,third);ledger.reserve()
    ledger.record({'leg':'third_models_route','stopped':True,'http_status':404,'calls_reserved_total':3})
    ledger.close();return first,second,third


@pytest.mark.asyncio
async def test_fourth_one_request_inherits_all_without_changing_prior_files(tmp_path):
    paths=chain(tmp_path);before=[p.read_bytes() for p in paths]
    destination=tmp_path/'v4.json';ledger=FourthLedger(*paths,destination)
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(return_value=SimpleNamespace(data=[SimpleNamespace(id='openai/gpt-oss-120b',active=True)]))))
    try:
        await list_once(ledger,client)
        assert ledger.state['calls_reserved_total']==4
        assert ledger.state['events'][-1]['requests_remaining']==4
        assert ledger.state['events'][-1]['active_model_ids']==['openai/gpt-oss-120b']
        assert [p.read_bytes() for p in paths]==before
        with pytest.raises(AcceptanceStopped):await list_once(ledger,client)
        assert client.models.list.call_count==1
    finally:ledger.close()
    with pytest.raises(FileExistsError):FourthLedger(*paths,destination)


@pytest.mark.asyncio
async def test_fourth_failure_is_spent_no_raw_body(tmp_path,capsys):
    paths=chain(tmp_path);ledger=FourthLedger(*paths,tmp_path/'v4.json')
    client=SimpleNamespace(models=SimpleNamespace(list=AsyncMock(side_effect=RuntimeError('hidden raw body'))))
    try:
        await list_once(ledger,client)
        assert ledger.state['calls_reserved_total']==4
        assert 'hidden raw body' not in capsys.readouterr().out
    finally:ledger.close()


def test_changed_chain_or_wrong_usage_refused(tmp_path):
    paths=chain(tmp_path);row=json.loads(paths[2].read_text());row['calls_reserved_total']=2
    paths[2].write_text(json.dumps(row))
    with pytest.raises(AcceptanceStopped):FourthLedger(*paths,tmp_path/'v4.json')
