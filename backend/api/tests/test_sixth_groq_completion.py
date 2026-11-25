import json
from types import SimpleNamespace
import pytest
from tests.test_fifth_groq_completion import prior
from scripts.accept_one_groq_completion import FifthLedger, completion_once
from scripts.accept_sixth_groq_completion import SixthLedger
from scripts.accept_dev_cart import AcceptanceStopped


def five(tmp_path):
    paths=prior(tmp_path);dest=tmp_path/'v5.json';ledger=FifthLedger(*paths,dest)
    ledger.reserve_call();ledger.record({'leg':'completion5','stopped':True,'error_class':'BadRequestError',
        'calls_reserved_total':5,'requests_remaining':3});ledger.close()
    return (*paths,dest)


def test_sixth_preserves_all_five_and_reserves_once(tmp_path):
    paths=five(tmp_path);before=[p.read_bytes() for p in paths];dest=tmp_path/'v6.json'
    ledger=SixthLedger(*paths,dest)
    try:
        assert ledger.state['inherited_calls']==5
        ledger.reserve_call();assert ledger.state['calls_reserved_total']==6
        assert [p.read_bytes() for p in paths]==before
        with pytest.raises(AcceptanceStopped):ledger.reserve_call()
    finally:ledger.close()
    with pytest.raises(FileExistsError):SixthLedger(*paths,dest)


@pytest.mark.parametrize('field,value',[('calls_reserved_total',4),('schema_version',4),('approval','other')])
def test_unreviewed_fifth_blocks_before_destination(tmp_path,field,value):
    paths=five(tmp_path);row=json.loads(paths[-1].read_text());row[field]=value
    paths[-1].write_text(json.dumps(row));dest=tmp_path/'v6.json'
    with pytest.raises(AcceptanceStopped):SixthLedger(*paths,dest)
    assert not dest.exists()


@pytest.mark.asyncio
async def test_sixth_failure_counts_and_keeps_only_safe_fields(tmp_path,capsys):
    paths=five(tmp_path);ledger=SixthLedger(*paths,tmp_path/'v6.json');service=SimpleNamespace()
    async def recommend(q,context):
        ledger.reserve_call();service.acceptance_error='BadRequestError'
        service.acceptance_error_metadata={'http_status':400,'provider_code':'json_validate_failed',
                                          'provider_param':'response_format','request_id':'req_abcdefgh1234'}
    service.filter_and_recommend=recommend
    try:
        await completion_once(ledger,service,[{'id':1},{'id':2}],leg='completion6',remaining=2)
        row=ledger.state['events'][-1]
        assert row['leg']=='completion6' and row['requests_remaining']==2
        assert row['calls_reserved_total']==6 and row['error_metadata']['http_status']==400
    finally:ledger.close()
