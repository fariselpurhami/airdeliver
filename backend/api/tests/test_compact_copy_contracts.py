"""Explicit safety/UX obligations survive prompt de-duplication, no provider."""
import json
import pytest
from app.services.compact_copy_contracts import contracts
from app.services.shopping_copy import write_shopping_copy,ShoppingDraft,GroundingReview
from app.services.shared_provider_admission import estimated_tokens
from app.services.structured_output import response_format
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row

# Semantic coverage signposts. Runtime and separate review tests remain necessary;
# string presence is not a model-entailment certification.
REQUIRED={
 'source_and_injection':['untrusted data','Only supplied cards','never history','model knowledge'],
 'identity_claims':['exact name claim','spec.KEY','stringified catalog_specs','Empty IDs/claims'],
 'stock_synthetic':['not merchant verified','synthetic tests','no DEMO badge'],
 'nonrepresentation':['action/payment/reservation/procurement/escalation promises','Claims do not authorize shopping changes'],
 'hard_constraints':['all hard constraints','never silently relax'],
 'privacy_tone':['exact sentiment_evidence','tone only','current words win','private profile'],
 'alternatives':['same-purpose evidence','never global','outside_budget is not out-of-stock'],
 'tasks':['target_searches','no borrowing specs','no invented discount','listed price/currency'],
 'customer_experience':['specific unknown','low-pressure','varied relevant wording','never invented certainty'],
  'no_invented_offers':['next step the shop really has','never offer holds, alerts, monitoring, notifications'],
}
@pytest.mark.parametrize('name,phrases',REQUIRED.items())
def test_writer_obligation_coverage(name,phrases):
 writer,_=contracts('catalog_results',{'product_answer_shape':'four_phase'})
 assert all(p in writer for p in phrases),(name,phrases)

@pytest.mark.parametrize('phrases',[
 ['untrusted data','Only supplied cards','exact name claim','Local stock is not merchant verified'],
 ['Independently review','implied claims','All must be true','do not infer support'],
 ['four generic filler paragraphs fails','no borrowing specs','no invented discount'],
 ['synthetic tests','hard constraints','not authority for another action'],
])
def test_independent_reviewer_has_its_own_complete_gate(phrases):
 _,review=contracts('catalog_results',{'product_answer_shape':'four_phase'})
 assert all(p in review for p in phrases)

@pytest.mark.parametrize('mode,ctx,expected,absent',[
 ('clarification',{},'IDs/claims empty','exactly four nonempty sections'),
 ('conversation',{},'Conversation stays naturally','exactly four nonempty sections'),
 ('catalog_results',{'gift_browse':True},'Exactly one follow-up','exactly four nonempty sections'),
 ('catalog_results',{'sales_intent':'OPENING_INSIGHT'},'exactly two short paragraphs','exactly four nonempty sections'),
])
def test_mode_exceptions(mode,ctx,expected,absent):
 writer,review=contracts(mode,ctx)
 assert expected in writer and expected in review and absent not in writer

@pytest.mark.asyncio
async def test_actual_writer_review_pair_reduction_without_data_or_call_loss():
 seen=[]
 async def infer(messages):
  seen.append(messages)
  return json.dumps(dict(text='Compare the listed design.',product_ids=[],claims=[]) if len(seen)==1 else dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 card=catalog_result(row())
 await write_shopping_copy(infer,'headphones',[card],{},'catalog_results',1,{'product_answer_shape':'four_phase'})
 assert len(seen)==2 and 'Independently review' in seen[1][0]['content']
 assert json.loads(seen[1][1]['content'])['input']==json.loads(seen[0][1]['content'])
 pair=estimated_tokens(seen[0],response_format('openai/gpt-oss-120b',ShoppingDraft))+640+estimated_tokens(seen[1],response_format('openai/gpt-oss-120b',GroundingReview))+256
 assert pair<4700  # Previous same-fixture pair5952, not a full rolling-quota promise.
