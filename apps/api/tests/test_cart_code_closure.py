from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_cart_service import AICartService
from app.services.ai_nlu_service import AINLUService,InternalCommand,CommerceIntentPayload,IntentCategory,CartActionType,RequestContext
from tests.test_cart_persistence_outcomes import real_cache

@pytest.mark.asyncio
async def test_direct_clear_cannot_touch_order_database(real_cache):
    cache,_=real_cache
    await cache.set_json_required('ai_cart:17',{'items':[],'total':'0','updated_at':'fixture'},ttl=60)
    db=SimpleNamespace(execute=AsyncMock(side_effect=AssertionError('must not query orders')),commit=AsyncMock())
    service=AICartService(db,cache,None);service.handle_sync_cart=AsyncMock()
    await service.handle_clear_cart({'user_id':17})
    db.execute.assert_not_awaited();db.commit.assert_not_awaited()
    assert await cache.get_json_required('ai_cart:17') is None

@pytest.mark.asyncio
@pytest.mark.parametrize('route',['internal_clear','internal_save','text_clear','smart_clear'])
async def test_retained_clear_save_paths_prepare_review_without_mutation(real_cache,route):
    cache,_=real_cache
    before={'items':[{'product_id':7,'name':'Item','quantity':1,'price':'20'}],'total':'20','updated_at':'fixture'}
    await cache.set_json_required('ai_cart:17',before,ttl=60)
    svc=AINLUService(object(),object(),SimpleNamespace(publish=AsyncMock()),cache,object());svc._send_to_ui=AsyncMock()
    if route.startswith('internal'):await svc._process_internal_command(17,InternalCommand.CLEAR_CART.value if route.endswith('clear') else InternalCommand.SAVE_FOR_LATER.value)
    elif route=='text_clear':assert await svc._handle_text_commands(17,'clear cart',{})
    else:assert await svc._handle_smart_cart_action(17,CommerceIntentPayload(category=IntentCategory.CART_ACTION,is_chitchat=False,cart_action_type=CartActionType.CLEAR),RequestContext(17,'test',0))
    assert await cache.get_json_required('ai_cart:17')==before
    svc.rabbitmq.publish.assert_not_awaited()
    payload=svc._send_to_ui.await_args.args[1]
    assert payload['action']['action']=='review_cart_lifecycle' and 'Nothing has changed' in payload['content']

@pytest.mark.asyncio
async def test_negated_clear_phrase_does_not_trigger_legacy_text_side_effect():
    svc=AINLUService(object(),object(),SimpleNamespace(publish=AsyncMock()),object(),object())
    assert not await svc._handle_text_commands(17,'do not clear cart',{})
    svc.rabbitmq.publish.assert_not_awaited()
