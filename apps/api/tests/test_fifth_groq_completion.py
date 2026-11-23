import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from tests.test_fourth_groq_route import chain
from scripts.verify_corrected_groq_route import FourthLedger
from scripts.accept_one_groq_completion import FifthLedger, completion_once, MODEL
from scripts.accept_dev_cart import AcceptanceStopped


def prior(tmp_path):
    paths=chain(tmp_path);fourth=tmp_path/'v4.json';ledger=FourthLedger(*paths,fourth);ledger.reserve()
    ledger.record({'leg':'corrected_models_route','success':True,'calls_reserved_total':4,'active_model_ids':[MODEL]})
    ledger.close();return (*paths,fourth)


def test_fifth_inherits_hashes_and_refuses_budget_reset(tmp_path):
    paths=prior(tmp_path);before=[p.read_bytes() for p in paths];dest=tmp_path/'v5.json'
    ledger=FifthLedger(*paths,dest)
    try:
        ledger.reserve_call();assert ledger.state['calls_reserved_total']==5
        assert [p.read_bytes() for p in paths]==before
        with pytest.raises(AcceptanceStopped):ledger.reserve_call()
    finally:ledger.close()
    with pytest.raises(FileExistsError):FifthLedger(*paths,dest)


@pytest.mark.asyncio
async def test_output_keeps_raw_truncation_separate_from_fallback(tmp_path):
    paths=prior(tmp_path);ledger=FifthLedger(*paths,tmp_path/'v5.json')
    service=SimpleNamespace()
    async def recommend(q,context):
        ledger.reserve_call();service.acceptance_raw=SimpleNamespace(usage=SimpleNamespace(completion_tokens=256),
            choices=[SimpleNamespace(finish_reason='length',message=SimpleNamespace(content='{truncated'))])
        return SimpleNamespace(model_dump=lambda **kw:{'selected_ids':[2],'intro_message':'fallback'})
    service.filter_and_recommend=recommend
    try:
        await completion_once(ledger,service,[{'id':1},{'id':2}])
        row=ledger.state['events'][-1]
        assert row['finish_reason']=='length' and row['raw_text']=='{truncated'
        assert row['parsed']['intro_message']=='fallback'
        assert row['requests_remaining']==3
    finally:ledger.close()


def test_missing_reviewed_model_visibility_blocks_before_destination(tmp_path):
    paths=prior(tmp_path);row=json.loads(paths[3].read_text());row['events'][-1]['active_model_ids']=[]
    paths[3].write_text(json.dumps(row))
    with pytest.raises(AcceptanceStopped):FifthLedger(*paths,tmp_path/'v5.json')
