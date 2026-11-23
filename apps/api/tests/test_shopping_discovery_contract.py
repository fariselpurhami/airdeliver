"""Deterministic boundary/evaluation fixtures. Model transport is test-controlled;
no generated prose, fake product data or review bypass exists in shipped code."""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app.services.neural_core_service import NeuralCoreService, SessionMemory
from app.services.shopping_discovery import ShoppingBrief, catalog_result
from app.services.shopping_copy import ShoppingDraft, validate_draft, write_shopping_copy


def row(**kwargs):
    base=dict(id=1,name='Studio Headphones',sku='S1',price=Decimal('19.99'),currency='USD',inventory=4,
              is_active=True,category='audio',image=None,attributes={})
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_evidence_cannot_upgrade_local_inventory_to_merchant_stock():
    card=catalog_result(row())
    assert card.stock_status=='local_in_stock'
    assert card.evidence_kind=='local_catalog'
    assert 'not verified' in card.availability_note


@pytest.mark.parametrize('values',[{'attributes':{'_seed_dataset':'airdeliver-demo-v1'}},{'sku':'ADL-DEMO-v1-X'}])
def test_either_demo_marker_is_sufficient_for_synthetic_disclosure(values):
    card=catalog_result(row(**values))
    assert card.evidence_kind=='seeded_demo' and card.stock_status=='demo'
    assert 'synthetic' in card.availability_note


def test_unknown_price_stays_unknown_and_currency_is_never_dollars_by_inference():
    card=catalog_result(row(currency='EUR'))
    assert card.currency=='EUR'
    card=catalog_result(row(price='NaN'))
    assert card.price is None and card.currency is None and card.price_status=='unknown'
    assert catalog_result(row(is_active=False)) is None


@pytest.mark.parametrize('draft',[
    {'text':'Buy Phantom Watch','product_ids':[99],'claims':[]},
    {'text':'Studio Headphones cost 2.00','product_ids':[1],'claims':[{'product_id':1,'field':'price','value':'2.00'}]},
    {'text':'Studio Headphones','product_ids':[1],'claims':[]},
    {'text':'The price is 5.00','product_ids':[],'claims':[]},
    {'text':'Visit https://invalid.example','product_ids':[],'claims':[]},
])
def test_unbacked_product_price_or_link_is_rejected(draft):
    with pytest.raises(ValueError):validate_draft(ShoppingDraft(**draft),[catalog_result(row())])


@pytest.mark.asyncio
async def test_review_rejects_implied_stock_even_when_ids_are_valid():
    draft={'text':'Studio Headphones are available for immediate dispatch.','product_ids':[1],
           'claims':[{'product_id':1,'field':'name','value':'Studio Headphones'}]}
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(dict(supported=False,all_product_mentions_declared=True,
        no_unsupported_commercial_claims=False,fulfills_discovery_task=True))])
    with pytest.raises(ValueError,match='grounding_review_rejected'):
        await write_shopping_copy(infer,'headphones',[catalog_result(row())],{},'catalog_results',1)
    assert infer.await_count==2


@pytest.mark.asyncio
async def test_model_authored_clarification_survives_only_after_independent_review():
    infer=AsyncMock(side_effect=[json.dumps(dict(text='What would you like to spend, and what does your partner enjoy?',product_ids=[],claims=[])),
        json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])
    text=await write_shopping_copy(infer,'gift for my wife',[],{},'clarification',1)
    assert text=='What would you like to spend, and what does your partner enjoy?'


@pytest.mark.asyncio
@pytest.mark.parametrize('message,output',[
    ('I want to buy a gift for my wife',{'intent':'GIFT_DISCOVERY','brief':{'recipient':'wife'}}),
    ('عايز هدية لمراتي',{'intent':'GIFT_DISCOVERY','brief':{'recipient':'مراتي'}}),
    ('gift for my wife',{'intent':'PRODUCT_SEARCH','query':'Cartier LOVE Bracelet','search_subject':'Cartier LOVE Bracelet'}),
    ('gift for my wife',{'intent':'PRODUCT_SEARCH','query':'gift for my wife'}),
])
async def test_recipient_only_or_invented_subject_stays_discovery(message,output):
    svc=NeuralCoreService(object(),object());svc.is_healthy=True
    svc._execute_llm_inference=AsyncMock(return_value=json.dumps(output))
    decision=await svc._analyze_intent(message,SessionMemory(user_name='Client'))
    assert decision.intent=='GIFT_DISCOVERY'


@pytest.mark.asyncio
async def test_explicit_subject_can_advance_without_inventing_a_category():
    svc=NeuralCoreService(object(),object());svc.is_healthy=True
    svc._execute_llm_inference=AsyncMock(return_value=json.dumps(dict(intent='PRODUCT_SEARCH',query='headphones',search_subject='headphones')))
    decision=await svc._analyze_intent('headphones under USD100',SessionMemory(user_name='Client'))
    assert decision.intent=='PRODUCT_SEARCH'


@pytest.mark.asyncio
async def test_unavailable_writer_is_an_explicit_notice_not_sales_copy():
    svc=NeuralCoreService(object(),object());svc.is_healthy=False
    response=await svc._shopping_response('gift',[],ShoppingBrief(),'clarification','GIFT_DISCOVERY')
    assert response.response_kind=='system_notice' and response.text.startswith('System notice:')
    assert not response.products


def test_brief_drops_model_inferred_tastes():
    brief=ShoppingBrief(recipient='wife',preference='diamonds',budget='10000').grounded('gift for my wife')
    assert brief.recipient=='wife' and brief.preference is None and brief.budget is None


def test_explicit_budget_enforced_without_cross_currency_or_unpriced_candidates():
    brief=ShoppingBrief(budget='under USD 100',budget_max='100',budget_currency='USD').grounded('headphones under USD 100')
    assert brief.permits(catalog_result(row(price=99)))
    assert not brief.permits(catalog_result(row(price=101)))
    assert not brief.permits(catalog_result(row(price=20,currency='EUR')))
    assert not brief.permits(catalog_result(row(price='NaN')))
    invented=ShoppingBrief(budget='cheap',budget_max='100',budget_currency='USD').grounded('cheap headphones')
    assert invented.budget_max is None


@pytest.mark.asyncio
async def test_total_writer_review_deadline_fails_closed():
    import asyncio
    async def slow(messages):await asyncio.sleep(.05);return '{}'
    with pytest.raises(TimeoutError):
        await write_shopping_copy(slow,'gift',[],{},'clarification',.001)


def test_catalog_name_in_prose_cannot_hide_from_reference_contract():
    with pytest.raises(ValueError,match='undeclared_catalog_name'):
        validate_draft(ShoppingDraft(text='Studio Headphones look nice.',product_ids=[],claims=[]),[catalog_result(row())])


@pytest.mark.asyncio
async def test_invalid_draft_withholds_cards_too():
    svc=NeuralCoreService(object(),object());svc.is_healthy=True
    svc._execute_llm_inference=AsyncMock(return_value=json.dumps(dict(text='A phantom watch costs 5.00',product_ids=[999],claims=[])))
    result=await svc._shopping_response('gift',[catalog_result(row())],ShoppingBrief(),'catalog_results','PRODUCT_SEARCH')
    assert result.response_kind=='system_notice' and result.products==[]
    assert 'phantom' not in result.text


@pytest.mark.asyncio
async def test_two_turn_discovery_preserves_only_customer_preferences_and_never_searches_early():
    from app.services.neural_core_service import RouterDecision
    from tests.test_neural_session_isolation import Cache
    engine=SimpleNamespace(perform_hybrid_search_pure=AsyncMock())
    cache=Cache();svc=NeuralCoreService(engine,cache);svc.is_healthy=True
    svc._analyze_intent=AsyncMock(side_effect=[RouterDecision(intent='GIFT_DISCOVERY',brief=ShoppingBrief(recipient='wife')),
        RouterDecision(intent='GIFT_DISCOVERY',brief=ShoppingBrief(budget='under USD 100',budget_max='100',budget_currency='USD'))])
    verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(dict(text='What budget and interests should we explore?',product_ids=[],claims=[])),verdict,
        json.dumps(dict(text='What does she enjoy, or what occasion is the gift for?',product_ids=[],claims=[])),verdict])
    first=await svc.handle_message(None,'gift for my wife',None,'brief-session')
    second=await svc.handle_message(None,'under USD 100',None,'brief-session')
    assert first.response_kind==second.response_kind=='clarification'
    assert engine.perform_hybrid_search_pure.await_count==0
    stored=cache.data[svc._get_session_key('brief-session')]['shopping_brief']
    assert stored['recipient']=='wife' and stored['budget_max']=='100'


@pytest.mark.asyncio
async def test_social_misroute_cannot_publish_undeclared_product_without_review():
    svc=NeuralCoreService(object(),object());svc.is_healthy=True
    svc._execute_llm_inference=AsyncMock(side_effect=[json.dumps(dict(text='Cartier is perfect and available.',product_ids=[],claims=[])),
        json.dumps(dict(supported=False,all_product_mentions_declared=False,no_unsupported_commercial_claims=False,fulfills_discovery_task=False))])
    result=await svc._shopping_response('gift for my wife',[],ShoppingBrief(),'conversation','SOCIAL_CHAT')
    assert result.response_kind=='system_notice'
    assert 'Cartier' not in result.text
