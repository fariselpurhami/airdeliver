import asyncio,json
from unittest.mock import AsyncMock
import pytest
from app.services.product_knowledge_service import answer_product_question
V={'supported':True,'exact_model':True,'product_information_only':True}

@pytest.mark.asyncio
@pytest.mark.parametrize('targets',[None,'Alpha',('Alpha',42),({},),('',),('A','B','C','D')])
async def test_bad_target_container_or_identity_never_calls_lookup_or_fallback(targets):
    lookup=AsyncMock();infer=AsyncMock();fallback=AsyncMock()
    result=await answer_product_question(infer,'compare',targets=targets,lookup=lookup,fallback=fallback)
    assert result.confidence==0
    lookup.assert_not_awaited();infer.assert_not_awaited();fallback.assert_not_awaited()

@pytest.mark.asyncio
async def test_duplicate_normalized_targets_lookup_once_and_do_not_repeat_missing():
    lookup=AsyncMock(return_value=[{'url':'https://maker.example/a','text':'Alpha uses wood.'}])
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':['Alpha'],'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]}),json.dumps(V)])
    result=await answer_product_question(infer,'Alpha',targets=('Alpha',' alpha ','Alpha'),lookup=lookup)
    assert result.confidence>0 and lookup.await_count==1
    assert json.loads(infer.await_args_list[0].args[0][1]['content'])['requested_targets']==['Alpha']

@pytest.mark.asyncio
@pytest.mark.parametrize('coverage',[['Alpha','Beta'],['Alpha','Alpha'],['Al']])
async def test_covered_targets_need_individual_literal_quote_evidence_even_if_reviewer_would_pass(coverage):
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':coverage,'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]}),json.dumps(V)])
    result=await answer_product_question(infer,'compare Alpha Beta',targets=('Alpha','Beta'),lookup=AsyncMock(return_value=[{'url':'https://maker.example/a','text':'Alpha uses wood.'}]))
    assert result.confidence==0 and 'Source 1:' not in result.text and infer.await_count==1

@pytest.mark.asyncio
async def test_partial_source_failure_cannot_be_covered_by_sibling_quote():
    async def lookup(q):
        if q.startswith('Beta'):raise ConnectionError('private')
        return [{'url':'https://maker.example/a','text':'Alpha uses wood.'}]
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':['Alpha'],'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]}),json.dumps(V)])
    result=await answer_product_question(infer,'compare',targets=('Alpha','Beta'),lookup=lookup)
    assert 'not verified for: Beta' in result.text and 'Source 1: https://maker.example/a' in result.text
