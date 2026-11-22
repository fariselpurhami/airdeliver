import pytest
from app.services.neural_core_service import NeuralCoreService


def test_tracking_proposal_does_not_claim_tracking_executed():
    response = NeuralCoreService(object(), object())._handle_order_tracking('123')
    assert response.action.action == 'track_order'
    assert 'not been checked' in response.text
    assert 'satellite' not in response.text.lower()


def test_handoff_proposal_does_not_claim_handoff_executed():
    response = NeuralCoreService(object(), object())._handle_support_handoff()
    assert response.action.action == 'initiate_support_handoff'
    assert 'not been connected' in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize('visual', [False, True])
async def test_inventory_record_does_not_prove_dispatch_or_restock(visual):
    from types import SimpleNamespace
    class Engine:
        async def perform_hybrid_search_pure(self, *args, **kwargs):
            return [SimpleNamespace(name='Headphones', price=10, inventory=5)]
        async def search_by_image_vector(self, *args, **kwargs):
            return await self.perform_hybrid_search_pure()
    service = NeuralCoreService(Engine(), object())
    response = await service._handle_visual_search('image') if visual else await service._handle_product_search(None, 'headphones')
    assert 'in stock' in response.text
    assert 'not been verified' in response.text
    assert 'immediate dispatch' not in response.text
