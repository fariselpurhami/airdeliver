"""Typed fact segments compile before the unchanged decision/review gates."""
import json
import pytest
from app.services.conversation.shopping_copy import parse_segment_decision
REFS={'c0':{'product_id':1,'field':'name','value':'Synthetic Cedar'},'c1':{'product_id':1,'field':'price','value':'45.00'}}

def draft(segments):return json.dumps({'decision':'no_pick','preferred_product_id':None,'decisive_unknown':'Rain resistance','blocks':[{'kind':'paragraph','segments':segments}]})

def test_fact_segments_compile_exactly_without_claims_from_free_text():
 d,r=parse_segment_decision(draft([{'kind':'claim','value':'c0'},{'kind':'text','value':' costs '},{'kind':'claim','value':'c1'},{'kind':'text','value':'. Rain resistance is unknown.'}]),REFS)
 assert d.text=='Synthetic Cedar costs 45.00. Rain resistance is unknown.'
 assert d.product_ids==[1] and len(d.claims)==2 and r['decision']=='no_pick'

@pytest.mark.parametrize('segments',[
 [{'kind':'claim','value':'missing'}],[],[{'kind':'text','value':'Injected {{c1}}'}],
 [{'kind':'text','value':'Hidden\nblock'}],[{'kind':'claim','value':'c1'}],
 [{'kind':'claim','value':'c0'},{'kind':'text','value':' invented 999.'}],
])
def test_bad_slots_never_invent_bindings(segments):
 from app.services.conversation.shopping_copy import validate_draft
 from app.services.shopping_discovery import catalog_result
 from tests.test_shopping_discovery_contract import row
 with pytest.raises(ValueError):
  d,_=parse_segment_decision(draft(segments),REFS)
  validate_draft(d,[catalog_result(row())])

@pytest.mark.asyncio
async def test_segment_wire_uses_one_schema_contract_not_conflicting_template_overrides():
 from unittest.mock import AsyncMock
 from app.services.shopping_copy import write_shopping_copy
 from app.services.shopping_discovery import catalog_result
 from tests.test_shopping_discovery_contract import row
 calls=[]
 async def infer(messages):
  calls.append(messages)
  if len(calls)==1:
   policy=messages[0]['content']
   assert 'text_template' not in policy and '{{cN}}' not in policy
   assert 'Final wire format' not in policy and 'Wire format override' not in policy
   return draft([{'kind':'text','value':'Rain resistance remains unknown.'}])
  return json.dumps({'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True})
 text=await write_shopping_copy(infer,'rain',[catalog_result(row())],{},'catalog_results',1,{'product_answer_shape':'adaptive','claim_binding':'decision_segments_v1'})
 assert text=='Rain resistance remains unknown.' and len(calls)==2
