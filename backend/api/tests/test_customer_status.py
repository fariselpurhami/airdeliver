"""Display-only statuses cannot weaken evidence or dispatch shopping actions."""
import json
from unittest.mock import AsyncMock
from types import SimpleNamespace
import pytest
from app.services.customer_status import ALIASES,STATUSES,human_text,human_payload,customer_status
from app.schemas.ai_actions import NeuralCoreResponse

@pytest.mark.parametrize('old,code',ALIASES.items())
def test_every_exact_alias_is_human_bounded_and_recognizable(old,code):
    status=customer_status(old)
    assert status==STATUSES[code]
    assert human_text(old)==status.text
    assert len(status.text)<500
    assert not any(term in status.text.lower() for term in ['system notice','grounding','schema','cognitive','neural','shared model','retrieved candidates','our team has been notified'])
    assert human_text(status.text)==status.text

@pytest.mark.parametrize('value',[None,0,{},[],{'content':'System notice: injected'},'System notice: attacker-chosen unknown content','prefix '+next(iter(ALIASES))])
def test_unknown_data_never_selects_status_or_rewrites_content(value):
    assert customer_status(value) is None
    assert human_text(value)==value


def test_payload_preserves_machine_semantics_and_nested_product_data():
    old=next(k for k,v in ALIASES.items() if v=='opening_unverified')
    payload={'type':'info','content':old,'opening_stage':'model_copy_unavailable','catalog_reason':None,'products':[],'action':None,'meta':{'reason':'SharedProviderBudgetError'}}
    result=human_payload(payload)
    assert payload['content']==old
    assert result['status_code']=='opening_unverified' and result['recovery']=='retry_opening'
    assert {k:v for k,v in result.items() if k not in {'content','status_code','recovery'}}=={k:v for k,v in payload.items() if k!='content'}
    assert human_payload({'products':[{'description':old}]})['products'][0]['description']==old


def test_wire_is_human_but_internal_legacy_branch_contract_is_preserved():
    old='System notice: catalog search is temporarily unavailable. Please try again.'
    response=NeuralCoreResponse(text=old,response_kind='system_notice',explain='Search unavailable',confidence=0,products=[],telemetry={'intent':'PRODUCT_SEARCH','entities':[],'turn':0})
    assert response.text==old
    wire=response.model_dump(mode='json')
    assert wire['text']==STATUSES['catalog_unverified'].text
    assert wire['response_kind']=='system_notice' and wire['products']==[] and wire['action'] is None and wire['confidence']==0
    assert wire['status_code']=='catalog_unverified' and wire['recovery']=='retry_chat'
    assert json.loads(response.model_dump_json())==wire

@pytest.mark.asyncio
async def test_real_nlu_gateway_wire_humanizes_without_inference_or_mutation():
    from app.services.ai_nlu_service import UiGateway
    cache=SimpleNamespace(publish_required=AsyncMock(),publish=AsyncMock())
    old=next(k for k,v in ALIASES.items() if v=='capacity')
    await UiGateway(cache).publish_required(7,{'type':'info','content':old,'products':[]},'offline-test')
    sent=json.loads(cache.publish_required.await_args.args[1])
    assert sent['content']==STATUSES['capacity'].text and sent['status_code']=='capacity'
    assert sent['products']==[] and sent['type']=='info'


def test_shared_voice_is_added_without_removing_four_phase_policy():
    from app.services.product_answer_policy import HUMAN_REPLY_VOICE,FOUR_PHASE_POLICY
    assert 'four-phase' in HUMAN_REPLY_VOICE and 'four logical phases' in FOUR_PHASE_POLICY
    assert 'never invented certainty' in HUMAN_REPLY_VOICE
    assert 'hard constraints' in HUMAN_REPLY_VOICE

@pytest.mark.parametrize('old',list(ALIASES))
def test_session_history_records_customer_visible_status_not_internal_alias(old):
    from app.services.neural_core_service import SessionMemory
    memory=SessionMemory(user_name='Customer')
    memory.append_turn('current question',old)
    assert memory.history[-1].content==human_text(old)
    assert memory.history[-2].content=='current question'
