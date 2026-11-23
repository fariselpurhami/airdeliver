from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.neural_core_service import NeuralCoreService,RouterDecision,SessionMemory

@pytest.mark.asyncio
async def test_review_requires_user_exact_unique_catalog_match_and_no_mutation():
 product=SimpleNamespace(id=7,name='Atlas headphones',is_active=True,inventory=5,price='25.00',currency='USD')
 engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=[product]))
 service=NeuralCoreService(engine,object());db=SimpleNamespace(get=AsyncMock(return_value=product))
 decision=RouterDecision(intent='CART_ADD',query='Atlas headphones',quantity=2)
 response=await service._handle_cart_review(db,decision,SimpleNamespace(id=1))
 assert response.action.action=='review_cart_change'
 assert response.action.payload.product_id==7 and response.action.payload.quantity==2
 assert 'not changed' in response.text and 'user_id' not in response.action.payload.model_dump()
 assert (await service._handle_cart_review(db,decision,None)).action is None
 decision.query='those';assert (await service._handle_cart_review(db,decision,SimpleNamespace(id=1))).action is None
 engine.perform_hybrid_search_pure.return_value=[product,product];decision.query='Atlas headphones'
 assert (await service._handle_cart_review(db,decision,SimpleNamespace(id=1))).action is None

@pytest.mark.asyncio
async def test_remove_review_names_entire_line_and_rechecks_catalog():
 product=SimpleNamespace(id=7,name='Atlas headphones',is_active=True,inventory=0,price='25.00',currency='USD')
 engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock(return_value=[product]))
 service=NeuralCoreService(engine,object());db=SimpleNamespace(get=AsyncMock(return_value=product))
 response=await service._handle_cart_review(db,RouterDecision(intent='CART_REMOVE',query=product.name),SimpleNamespace(id=1))
 assert response.action.payload.operation=='remove' and 'entire' in response.text
 product.currency='EUR'
 assert (await service._handle_cart_review(db,RouterDecision(intent='CART_ADD',query=product.name),SimpleNamespace(id=1))).action is None

@pytest.mark.asyncio
async def test_router_cannot_invent_mutation_target_not_named_by_customer(monkeypatch):
 service=NeuralCoreService(object(),object());service.is_healthy=True
 service._execute_llm_inference=AsyncMock(return_value='{"intent":"CART_ADD","query":"Atlas headphones","quantity":2}')
 response=await service._analyze_intent('add something',SessionMemory(user_name='Fixture'))
 assert response.query is None


@pytest.mark.asyncio
async def test_router_cannot_invent_nondefault_quantity(monkeypatch):
 service=NeuralCoreService(object(),object());service.is_healthy=True
 service._execute_llm_inference=AsyncMock(return_value='{"intent":"CART_ADD","query":"Atlas headphones","quantity":99}')
 response=await service._analyze_intent('add Atlas headphones',SessionMemory(user_name='Fixture'))
 assert response.query is None
 response=await service._analyze_intent('add99 Atlas headphones',SessionMemory(user_name='Fixture'))
 assert response.query is None
 response=await service._analyze_intent('add 99 Atlas headphones',SessionMemory(user_name='Fixture'))
 assert response.query=='Atlas headphones'
