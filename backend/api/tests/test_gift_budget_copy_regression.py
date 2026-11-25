"""Owner two-turn gift regression, no external inference."""
import json
import logging
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_discovery import ShoppingBrief
from app.services.shopping_copy import ShoppingDraft, validate_draft, ShoppingCopyError, write_shopping_copy
from app.services.sales_response_service import SalesResponseService, SalesResponseRequest


@pytest.mark.parametrize('source',['1000 dollar','1000 dollars','1000 US dollars','USD 1000','$1000'])
def test_explicit_dollar_words_ground_customer_cap(source):
    brief=ShoppingBrief(category='jewelry',budget=source,budget_max='1000',budget_currency='USD').grounded('Her birthday, I want jewelry and a budget '+source)
    assert brief.budget_max=='1000' and brief.budget_currency=='USD'


@pytest.mark.parametrize('text',['Your budget is 1000 dollars. Compare the cards below.','Within your 1000 dollar budget, compare these cards.'])
def test_grounded_budget_number_is_not_mistaken_for_product_price(text):
    validate_draft(ShoppingDraft(text=text),[],brief={'budget_max':'1000'})


@pytest.mark.parametrize('text',['This necklace costs 1000 dollars.','This item has 1000 diamonds.','Your budget is 900 dollars.'])
def test_customer_budget_never_authorizes_product_price_spec_or_other_amount(text):
    with pytest.raises(ValueError):validate_draft(ShoppingDraft(text=text),[],brief={'budget_max':'1000'})


@pytest.mark.asyncio
async def test_honest_empty_results_model_response_is_success_not_notice():
    draft={'text':'No matching jewelry appeared in these catalog results within your 1000 dollar budget. Would you like to broaden the style?','product_ids':[],'claims':[]}
    verdict=dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(verdict)])
    result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(SalesResponseRequest(
        message='Her birthday, and I want jewelry at range 1000 dollar',products=(),brief=ShoppingBrief(category='jewelry',budget='1000 dollar',budget_max='1000',budget_currency='USD'),mode='catalog_results',intent='PRODUCT_SEARCH'))
    assert result.response_kind=='catalog_results' and result.text==draft['text'] and result.products==[]


@pytest.mark.asyncio
@pytest.mark.parametrize('stage,values',[('writer_provider',[ConnectionError('PRIVATE secret')]),('writer_schema',['bad json']),('writer_evidence',[json.dumps({'text':'Price 999','product_ids':[],'claims':[]})]*2),('review_provider',[json.dumps({'text':'Compare the cards','product_ids':[],'claims':[]}),ConnectionError('PRIVATE secret')]),('review_verdict',[json.dumps({'text':'Compare the cards','product_ids':[],'claims':[]}),json.dumps(dict(supported=False,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))])])
async def test_failure_stage_is_safe_and_specific(stage,values,caplog):
    with caplog.at_level(logging.WARNING):
        result=await SalesResponseService(AsyncMock(side_effect=values),provider_ready=True,timeout=1).respond(SalesResponseRequest(message='jewelry',products=(),brief=ShoppingBrief(),mode='catalog_results',intent='PRODUCT_SEARCH'))
    record=next(r for r in caplog.records if str(r.msg).startswith('sales_response.copy_withheld'))
    assert record.copy_stage==stage and record.candidate_count==0
    assert 'PRIVATE' not in str(record.__dict__) and 'secret' not in str(record.__dict__)
    from app.core.logging_config import JsonFormatter
    for text in (False,True):
        rendered=JsonFormatter(text=text).format(record)
        assert stage in rendered and 'candidates=0' in rendered
    assert result.response_kind=='system_notice'


@pytest.mark.asyncio
@pytest.mark.parametrize('repaired',[True,False])
async def test_empty_evidence_numeric_violation_gets_one_bounded_model_repair(repaired):
    bad=json.dumps(dict(text='No ring under 50 dollars in current results.',product_ids=[],claims=[]))
    good=json.dumps(dict(text='No matching ring appeared in the current results within your stated budget. Would you like to broaden the style?',product_ids=[],claims=[]))
    verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    infer=AsyncMock(side_effect=[bad,good if repaired else bad,verdict])
    service=SalesResponseService(infer,provider_ready=True,timeout=1)
    result=await service.respond(SalesResponseRequest(message='Do you have a diamond ring under 50 dollars?',products=(),brief=ShoppingBrief(budget='50 dollars',budget_max='50',budget_currency='USD'),mode='catalog_results',intent='PRODUCT_SEARCH'))
    assert result.response_kind==('catalog_results' if repaired else 'system_notice')
    assert infer.await_count==(3 if repaired else 2)
    assert result.products==[]


@pytest.mark.parametrize('text',['Within your $50 budget, these results are empty.','Your 50 dollar cap does not yield a match.'])
def test_budget_echo_forms_are_scoped_to_customer_budget(text):
    validate_draft(ShoppingDraft(text=text),[],brief={'budget_max':'50'})
