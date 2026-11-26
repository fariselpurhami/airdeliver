"""A withheld recommendation must log a safe, fixed reason code (never model text)."""
import json,logging
from copy import deepcopy
from unittest.mock import AsyncMock
import pytest
from tests.test_llm_execution_limits import service,completion
from tests.test_reviewed_recommendation import P,D,V

async def _run(mode,caplog):
    llm=service();draft=deepcopy(D);verdict=dict(V)
    if mode=='numeric':draft['reasons'][0]['text']+=' Save 90 percent.'
    if mode=='reject':verdict['supported']=False
    if mode=='schema':draft={'intro':'SECRET-MODEL-TEXT','reasons':'bad'}
    async def respond(**kw):
        if kw['response_format'].get('json_schema',{}).get('name')=='GroundingReview':return completion(json.dumps(verdict))
        return completion(json.dumps(draft))
    llm._chat_completion=AsyncMock(side_effect=respond)
    with caplog.at_level(logging.WARNING):
        r=await llm.filter_and_recommend('show me a cotton shirt',[deepcopy(P)])
    assert r.selected_ids==[]
    return ' '.join(x.getMessage() for x in caplog.records if 'reviewed_recommendation_withheld' in x.getMessage())

@pytest.mark.asyncio
@pytest.mark.parametrize('mode,code',[('numeric','unsupported_numeric_or_link_claim'),('reject','Recommendation review rejected'.replace(' ','_').lower())])
async def test_withheld_logs_fixed_reason_code(mode,code,caplog):
    msg=await _run(mode,caplog)
    assert f'reason={code}' in msg

@pytest.mark.asyncio
async def test_unknown_error_text_is_never_logged(caplog):
    msg=await _run('schema',caplog)
    assert 'SECRET-MODEL-TEXT' not in msg and 'reason=schema_invalid' in msg
