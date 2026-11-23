"""Shared orchestration contract, no provider calls."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseRequest,SalesResponseService
from app.services.shopping_discovery import ShoppingBrief,catalog_result
from tests.test_shopping_discovery_contract import row


def request(**kwargs):
    values=dict(message='headphones',products=(catalog_result(row()),),brief=ShoppingBrief(),mode='catalog_results',intent='PRODUCT_SEARCH')
    values.update(kwargs);return SalesResponseRequest(**values)


def test_contract_refuses_unbounded_or_non_catalog_recommendations():
    with pytest.raises(ValueError):request(products=(catalog_result(row()),)*6)
    with pytest.raises(ValueError):request(mode='clarification')
    with pytest.raises(ValueError):request(products=(catalog_result(row()),catalog_result(row())))
    with pytest.raises(ValueError):SalesResponseService(AsyncMock(),provider_ready=True,timeout=0)


@pytest.mark.asyncio
async def test_evidence_snapshot_cannot_change_during_network_await():
    source=catalog_result(row());seen=[]
    verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    async def infer(messages):
        seen.append(json.loads(messages[1]['content']))
        if len(seen)==1:
            source.price='999.00'
            return json.dumps(dict(text='Compare the current catalog card below.',product_ids=[],claims=[]))
        return verdict
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(products=(source,)))
    assert result.products[0].price=='19.99'
    assert seen[1]['input']['catalog_evidence'][0]['price']=='19.99'


@pytest.mark.asyncio
async def test_shared_unavailable_provider_never_calls_transport_or_returns_cards():
    infer=AsyncMock()
    result=await SalesResponseService(infer,provider_ready=False,timeout=1).respond(request())
    assert result.response_kind=='system_notice' and result.products==[]
    infer.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_support_adapter_uses_same_shared_contract():
    from app.services.neural_core_service import NeuralCoreService
    svc=NeuralCoreService(object(),object());svc.is_healthy=True
    draft=json.dumps(dict(text='What interests should we explore?',product_ids=[],claims=[]))
    verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc._execute_llm_inference=AsyncMock(side_effect=[draft,verdict])
    result=await svc._shopping_response('gift',[],ShoppingBrief(),'clarification','GIFT_DISCOVERY')
    assert result.text=='What interests should we explore?' and result.response_kind=='clarification'
