from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import AINLUService,CartActionType,CommerceIntentPayload,IntentCategory,RequestContext


def service(success=True):
    svc=AINLUService(object(),object(),SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=success))),object(),object())
    svc._search_single_product=AsyncMock(return_value=[{'id':7,'name':'headphones'}])
    svc._safe_bundle_generation=AsyncMock(return_value=[])
    svc._send_to_ui=AsyncMock();svc._perform_devilish_recovery=AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_unconfirmed_broker_outcome_is_not_silently_successful():
    svc=service(False)
    with pytest.raises(RuntimeError):await svc._safe_publish({'user_id':1},'airdeliver.ai.cart.add')


@pytest.mark.asyncio
@pytest.mark.parametrize('action',[CartActionType.ADD,CartActionType.REMOVE])
async def test_published_cart_request_never_claims_mutation_already_executed(action):
    svc=service()
    intent=CommerceIntentPayload(category=IntentCategory.CART_ACTION,is_chitchat=False,cart_action_type=action,target_products=[{'product_name':'headphones'}])
    assert await svc._handle_smart_cart_action(1,intent,RequestContext(1,'local',0))
    body=svc._send_to_ui.call_args.args[1]['content']
    assert 'submitted' in body and 'confirm' in body
    assert 'Removed' not in body and "I've added" not in body
    assert svc.rabbitmq.publish.call_args.args[0]['notify_user'] is True
    if svc.tasks._tasks:
        import asyncio
        await asyncio.gather(*svc.tasks._tasks)


@pytest.mark.asyncio
async def test_failed_broker_emits_failure_not_success_and_does_not_fall_into_second_mutation_route():
    svc=service(False)
    intent=CommerceIntentPayload(category=IntentCategory.CART_ACTION,is_chitchat=False,cart_action_type=CartActionType.ADD,target_products=[{'product_name':'headphones'}])
    assert await svc._handle_smart_cart_action(1,intent,RequestContext(1,'local',0)) is True
    assert 'could not confirm' in svc._send_to_ui.call_args.args[1]['content']
    assert svc.rabbitmq.publish.call_count==1
