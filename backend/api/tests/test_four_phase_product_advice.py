"""Same writer/reviewer calls, original logical phases with honest evidence."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseService
from tests.test_sales_response_service import request

TEXT='Explore the listed choice for your current need.\n\nThe card contains current catalog details; unlisted specifications stay unknown.\n\nCompare those details with your requirements before deciding. Compatibility is unverified.\n\nCheck the missing details before choosing; no item is reserved.'
V=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)

@pytest.mark.asyncio
@pytest.mark.parametrize('task',['search','comparison','consultation','specifications','setup','negotiation','objection'])
async def test_substantive_advice_has_explicit_adaptive_writer_and_independent_review(task):
    infer=AsyncMock(side_effect=[json.dumps(dict(text=TEXT,product_ids=[],claims=[])),json.dumps(V)])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(evidence={'shopping_task':task}))
    assert result.text==TEXT and len(result.text.split('\n\n'))==4
    assert infer.await_count==2
    writer,review=[call.args[0] for call in infer.await_args_list]
    assert 'Do not force four sections' in writer[0]['content']
    assert 'Reject repetitive filler' in review[0]['content']
    assert json.loads(writer[1]['content'])['request_evidence']['product_answer_shape']=='adaptive'
    assert json.loads(review[1]['content'])['input']['request_evidence']['product_answer_shape']=='adaptive'

@pytest.mark.asyncio
@pytest.mark.parametrize('mode,task,intent',[('catalog_results','price_inquiry','PRODUCT_SEARCH'),('clarification','search','GIFT_DISCOVERY'),('conversation','search','SOCIAL_CHAT'),('catalog_results','search','OPENING_INSIGHT')])
async def test_short_and_opening_exceptions_are_not_forced_into_four_phases(mode,task,intent):
    infer=AsyncMock(side_effect=[json.dumps(dict(text='What detail matters to you?',product_ids=[],claims=[])),json.dumps(V)])
    req=request(mode=mode,intent=intent,products=() if mode!='catalog_results' else request().products,evidence={'shopping_task':task,'sales_intent':intent})
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(req)
    assert result.text=='What detail matters to you?'
    assert 'exactly four nonempty sections' not in infer.await_args_list[0].args[0][0]['content']

@pytest.mark.asyncio
async def test_reviewer_can_withhold_bad_shape_without_repair_or_extra_calls():
    infer=AsyncMock(side_effect=[json.dumps(dict(text=TEXT,product_ids=[],claims=[])),json.dumps({**V,'fulfills_discovery_task':False})])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request())
    assert result.response_kind=='system_notice' and result.products==[] and infer.await_count==2

@pytest.mark.asyncio
@pytest.mark.parametrize('task,goal,strategy',[
 ('search',None,'evidence_and_unknowns'),('price_inquiry',None,'listed_price_only'),
 ('objection',None,'explicit_concern_and_evidenced_options'),('negotiation',None,'explicit_concern_and_evidenced_options'),
 ('search','hesitation','explicit_concern_and_evidenced_options')])
async def test_safe_strategy_crosswalk_uses_task_not_hidden_profile(task,goal,strategy):
    infer=AsyncMock(side_effect=[json.dumps(dict(text=TEXT,product_ids=[],claims=[])),json.dumps(V)])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(evidence={'shopping_task':task,'advice_goal':goal}))
    assert result.text==TEXT
    payload=json.loads(infer.await_args_list[0].args[0][1]['content'])
    assert payload['request_evidence']['advisory_strategy']==strategy
    for call in infer.await_args_list:
        assert 'never infer fraud/nonexistence from absent results' in call.args[0][0]['content']


def test_legacy_unsafe_policy_symbols_only_read_by_preserved_unreviewed_bodies():
    import ast
    from pathlib import Path
    tree=ast.parse(Path('app/services/conversation/ai_nlu_service.py').read_text());reads=[]
    tracked={'UNIVERSAL_4_PHASE_ARCHITECTURE','_build_retention_directive','_get_dynamic_prompt_policy','_resolve_retention_mode'}
    def visit(node,scope=()):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):scope=(*scope,node.name)
        if isinstance(node,ast.Name) and isinstance(node.ctx,ast.Load) and node.id in tracked and scope:
            reads.append((scope[0],node.id))
        for child in ast.iter_child_nodes(node):visit(child,scope)
    visit(tree)
    assert reads
    assert all(name.endswith('_legacy_unreviewed') for name,symbol in reads),reads
