"""Malformed source acquisition is isolated per target, never semantic proof."""
import asyncio,json
from unittest.mock import AsyncMock
import pytest
from app.services.product_knowledge_service import answer_product_question,allowed_url
V={'supported':True,'exact_model':True,'product_information_only':True}

@pytest.mark.parametrize('url',[None,42,{},[],True,'https://maker.example/'+'x'*2048])
def test_bad_url_type_is_false_not_exception(url):assert not allowed_url(url)

@pytest.mark.asyncio
@pytest.mark.parametrize('bad',[None,{},[None],[{'url':42,'text':'bad'}],[{'url':'https://maker.example/a','text':42}],[{'url':'https://maker.example/a','text':''}],[{'url':'https://maker.example/a','text':'x'*6001}]])
async def test_malformed_target_sources_do_not_destroy_independent_valid_target(bad):
    async def lookup(q):
        if q.startswith('Beta'):return bad
        return [{'url':'https://maker.example/a','text':'Alpha uses wood.','unexpected_private_metadata':'do-not-pass'}]
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':['Alpha'],'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]}),json.dumps(V)])
    result=await answer_product_question(infer,'compare',targets=('Alpha','Beta'),lookup=lookup)
    assert result.confidence>0 and 'not verified for: Beta' in result.text
    assert 'Source 1: https://maker.example/a' in result.text
    assert 'unexpected_private' not in str(infer.await_args_list) and 'do-not-pass' not in str(infer.await_args_list)

@pytest.mark.asyncio
async def test_all_bad_sources_use_fallback_once_without_writer():
    infer=AsyncMock();fallback=AsyncMock(return_value=type('Result',(),{'products':[],'response_kind':'clarification'})())
    result=await answer_product_question(infer,'Alpha',targets=('Alpha',),lookup=AsyncMock(return_value=[None]),fallback=fallback)
    assert result.response_kind=='clarification'
    fallback.assert_awaited_once();infer.assert_not_awaited()

@pytest.mark.asyncio
async def test_cancel_during_independent_review_does_not_publish_partial_facts():
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':['Alpha'],'facts':[{'label':'Material','quote':'Alpha uses wood.','source':0}]}),asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):await answer_product_question(infer,'Alpha',targets=('Alpha',),lookup=AsyncMock(return_value=[{'url':'https://maker.example/a','text':'Alpha uses wood.'}]))
