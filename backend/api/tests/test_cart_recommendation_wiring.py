"""Producer contracts and preserved legacy consumer characterization.
New production consumer is covered by test_cart_sales_postgres.py.
"""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from app.schemas.cart_recommendation import CartRecommendationEvent, CART_RECOMMENDATION_ROUTING_KEY
from app.services.ai_cart_service import AICartService
from tests.test_ai_cart_service import FakeDB, FakeCache, make_product
from app.services.orchestration.worker_entrypoint import WorkerRuntime


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['added', 'removed'])
async def test_acknowledged_cart_command_emits_read_only_event(operation):
    cache = FakeCache()
    broker = SimpleNamespace(publish=AsyncMock(return_value=SimpleNamespace(is_success=True)))
    service = AICartService(FakeDB(make_product()), cache, broker)
    if operation == 'removed':
        await service.handle_add_to_cart({'user_id': 1, 'product_id': 7, 'notify_user': False})
        assert broker.publish.call_count == 0
        await service.handle_remove_from_cart({'user_id': 1, 'product_id': 7})
    else:
        await service.handle_add_to_cart({'user_id': 1, 'product_id': 7})
    events = [call for call in broker.publish.call_args_list if call.args[1] == CART_RECOMMENDATION_ROUTING_KEY]
    assert len(events) == 1
    assert CartRecommendationEvent.model_validate(events[0].args[0]).operation == operation
    assert cache.sets


@pytest.mark.asyncio
async def test_failed_persistence_never_requests_recommendations():
    cache = FakeCache()
    cache.set_json_required = AsyncMock(side_effect=ConnectionError())
    broker = SimpleNamespace(publish=AsyncMock())
    with pytest.raises(Exception):
        await AICartService(FakeDB(make_product()), cache, broker).handle_add_to_cart({'user_id':1,'product_id':7})
    broker.publish.assert_not_called()


@pytest.mark.asyncio
async def test_unavailable_optional_broker_keeps_acknowledged_cart():
    cache = FakeCache()
    broker = SimpleNamespace(publish=AsyncMock(side_effect=ConnectionError()))
    await AICartService(FakeDB(make_product()), cache, broker).handle_add_to_cart({'user_id':1,'product_id':7})
    assert cache._cart['items'][0]['quantity'] == 1
    assert any(p['type'] == 'success_text' for _, p in cache.published)


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['added','removed'])
async def test_consumer_reads_catalog_emits_carousel_and_never_mutates(operation):
    cache = FakeCache({'items':[{'product_id':7,'name':'Shoes','quantity':1,'price':'19.99'}]} if operation == 'added' else None)
    product = SimpleNamespace(model_dump=lambda **kw:{'id':8,'name':'Current catalog item','price':'12.00'})
    engine = SimpleNamespace(generate_perfect_bundle=AsyncMock(return_value=[product]),find_genius_alternatives=AsyncMock(return_value=[product]))
    @asynccontextmanager
    async def session():
        yield FakeDB(make_product())
    runtime = WorkerRuntime.__new__(WorkerRuntime)
    runtime.wait_for_readiness = AsyncMock()
    runtime.services = SimpleNamespace(session_maker=session, cache=cache, rabbitmq=object(), commerce=engine)
    await runtime._legacy_cart_recommendation_observed({'version':1,'user_id':1,'product_id':7,'operation':operation})
    assert len(cache.published) == 1
    assert cache.published[0][1]['products'][0]['id'] == 8
    assert 'verified' in cache.published[0][1]['content'] or 'Compare' in cache.published[0][1]['content']
    assert cache.sets == [] and cache.deleted == []
    assert engine.generate_perfect_bundle.call_count == (operation == 'added')
    assert engine.find_genius_alternatives.call_count == (operation == 'removed')


@pytest.mark.asyncio
async def test_delayed_add_event_is_skipped_if_anchor_already_removed():
    cache = FakeCache()
    @asynccontextmanager
    async def session(): yield FakeDB(make_product())
    engine = SimpleNamespace(generate_perfect_bundle=AsyncMock())
    runtime=WorkerRuntime.__new__(WorkerRuntime)
    runtime.wait_for_readiness=AsyncMock()
    runtime.services=SimpleNamespace(session_maker=session,cache=cache,rabbitmq=object(),commerce=engine)
    await runtime._legacy_cart_recommendation_observed({'user_id':1,'product_id':7,'operation':'added'})
    engine.generate_perfect_bundle.assert_not_called()
    assert cache.published == []


@pytest.mark.parametrize('change',[{'user_id':True},{'product_id':0},{'version':2},{'operation':'clear'}])
def test_versioned_event_rejects_invalid_contract(change):
    with pytest.raises(ValidationError):
        CartRecommendationEvent.model_validate(dict({'user_id':1,'product_id':7,'operation':'added'},**change))

@pytest.mark.asyncio
@pytest.mark.parametrize('operation',['added','removed'])
async def test_membership_changed_during_search_suppresses_stale_advice(operation):
    anchor={'product_id':7,'name':'Shoes','quantity':1,'price':'19.99'}
    cache=FakeCache({'items':[anchor]} if operation=='added' else None)
    async def search(*args,**kwargs):
        cache._cart=None if operation=='added' else {'items':[anchor]}
        return [SimpleNamespace(id=8,model_dump=lambda **kw:{'id':8,'name':'Candidate','price':'12'})]
    engine=SimpleNamespace(generate_perfect_bundle=search,find_genius_alternatives=search)
    @asynccontextmanager
    async def session():yield FakeDB(make_product())
    runtime=WorkerRuntime.__new__(WorkerRuntime);runtime.wait_for_readiness=AsyncMock()
    runtime.services=SimpleNamespace(session_maker=session,cache=cache,rabbitmq=object(),commerce=engine)
    await runtime._legacy_cart_recommendation_observed({'user_id':1,'product_id':7,'operation':operation})
    assert cache.published==[]

@pytest.mark.asyncio
async def test_suggestions_exclude_anchor_current_cart_and_duplicate_products():
    cache=FakeCache({'items':[{'product_id':7,'name':'Shoes','quantity':1,'price':'19.99'},
                             {'product_id':8,'name':'Already owned cart','quantity':1,'price':'5'}]})
    def product(id):return SimpleNamespace(id=id,model_dump=lambda **kw:{'id':id,'name':'Candidate','price':'12'})
    engine=SimpleNamespace(generate_perfect_bundle=AsyncMock(return_value=[product(i) for i in [7,8,9,9,10]]))
    @asynccontextmanager
    async def session():yield FakeDB(make_product())
    runtime=WorkerRuntime.__new__(WorkerRuntime);runtime.wait_for_readiness=AsyncMock()
    runtime.services=SimpleNamespace(session_maker=session,cache=cache,rabbitmq=object(),commerce=engine)
    await runtime._legacy_cart_recommendation_observed({'user_id':1,'product_id':7,'operation':'added'})
    assert [p['id'] for p in cache.published[-1][1]['products']]==[9,10]
