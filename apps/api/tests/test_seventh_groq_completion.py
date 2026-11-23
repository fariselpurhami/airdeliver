import json
from types import SimpleNamespace
import pytest
from tests.test_fifth_groq_completion import prior
from scripts.accept_one_groq_completion import FifthLedger, completion_once
from scripts.accept_sixth_groq_completion import SixthLedger
from scripts.accept_seventh_groq_completion import SeventhLedger
from scripts.accept_dev_cart import AcceptanceStopped


def five(tmp_path):
    paths=prior(tmp_path);dest=tmp_path/'v5.json';ledger=FifthLedger(*paths,dest)
    ledger.reserve_call();ledger.record({'leg':'completion5','stopped':True,'error_class':'BadRequestError',
        'calls_reserved_total':5,'requests_remaining':3});ledger.close()
    return (*paths,dest)


def six(tmp_path):
    paths=five(tmp_path);dest=tmp_path/'v6.json';ledger=SixthLedger(*paths,dest)
    ledger.reserve_call();ledger.record({'leg':'completion6','stopped':True,'error_class':'BadRequestError',
        'calls_reserved_total':6,'requests_remaining':2,'error_metadata':{'http_status':400,'provider_code':'json_validate_failed'}})
    ledger.close();return (*paths,dest)


def test_seventh_inherits_all_six_without_reset(tmp_path):
    paths=six(tmp_path);before=[p.read_bytes() for p in paths];dest=tmp_path/'v7.json'
    ledger=SeventhLedger(*paths,dest)
    try:
        ledger.reserve_call();assert ledger.state['calls_reserved_total']==7
        assert [p.read_bytes() for p in paths]==before
        with pytest.raises(AcceptanceStopped):ledger.reserve_call()
    finally:ledger.close()
    with pytest.raises(FileExistsError):SeventhLedger(*paths,dest)


def test_changed_sixth_blocks_before_destination(tmp_path):
    paths=six(tmp_path);row=json.loads(paths[-1].read_text());row['events'][-1]['error_metadata']['provider_code']='other'
    paths[-1].write_text(json.dumps(row));dest=tmp_path/'v7.json'
    with pytest.raises(AcceptanceStopped):SeventhLedger(*paths,dest)
    assert not dest.exists()
