"""Actual prompt builders and Redis ledger, no provider traffic.

Usage observations are explicitly artificial accounting scenarios, not tokenizer
measurements or claims about a live model. No budget/model/review gate changes.
"""
import json
from types import SimpleNamespace
import pytest
from app.services.compact_router_contract import ROUTER_CONTRACT
from app.services.neural_core_service import RouterDecision
from app.services.shopping_copy import write_shopping_copy,ShoppingDraft,GroundingReview
from app.services.structured_output import response_format
from app.services.shared_provider_admission import shared_provider_slot,SharedProviderBudgetError,estimated_tokens
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row
from tests.test_cart_persistence_outcomes import real_cache

async def chain(question,history=(),specs=None):
 seen=[]
 async def infer(messages):
  seen.append(messages)
  return json.dumps(dict(text='Compare the listed design.',product_ids=[],claims=[]) if len(seen)==1 else dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
 await write_shopping_copy(infer,question,[catalog_result(row(attributes=specs or {'connection':'wired'}))],{},'catalog_results',1,{'product_answer_shape':'four_phase'})
 model='openai/gpt-oss-120b'
 return [
  ('router',[dict(role='system',content=ROUTER_CONTRACT),*history,dict(role='user',content=question)],response_format(model,RouterDecision),768),
  ('writer',seen[0],response_format(model,ShoppingDraft),640),
  ('review',seen[1],response_format(model,GroundingReview),256),
 ]

@pytest.mark.asyncio
@pytest.mark.parametrize('question,history,specs',[
 ('I need wired headphones',(),None),
 ('عايز سماعات سلكية للمكالمات',(),None),
 ('Compare the exact card',tuple(dict(role='user' if i%2==0 else 'assistant',content='Earlier exact customer constraint '+('تفصيل ' if i%2==0 else 'detail ')*30) for i in range(10)),None),
 ('Which listed design fits?',(),{f'attribute_{i}':'evidence '*30 for i in range(32)}),
])
async def test_actual_chain_reservation_sizes_are_visible_without_bypassing_gate(question,history,specs):
 stages=await chain(question,history,specs)
 amounts=[estimated_tokens(messages,wire)+output for _,messages,wire,output in stages]
 assert len(stages)==3 and stages[-1][0]=='review'
 assert all(amount>0 for amount in amounts)
 # Baseline is deliberately not a false promise that every chain fits7200.
 if history or specs:assert sum(amounts)>7200
 assert 'Independently review' in stages[-1][1][0]['content']

@pytest.mark.asyncio
async def test_unknown_cost_stops_before_review_and_never_publishes(real_cache):
 cache,_=real_cache;stages=await chain('I need wired headphones');sent=[]
 for stage,messages,wire,output in stages:
  try:
   async with shared_provider_slot('offline-chain-unknown',messages,wire,output,client=cache.client,limit=7200):sent.append(stage)
  except SharedProviderBudgetError:break
 assert sent==['router','writer']
 assert 'review' not in sent  # No review means no accepted/published response.

@pytest.mark.asyncio
async def test_artificial_low_usage_reconciliation_allows_review_and_next_router(real_cache):
 cache,_=real_cache;stages=await chain('I need wired headphones');sent=[]
 for stage,messages,wire,output in [*stages,stages[0]]:
  async with shared_provider_slot('offline-chain-artificial-low',messages,wire,output,client=cache.client,limit=7200) as r:
   sent.append(stage);r.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=400)))
 assert sent==['router','writer','review','router']
 keys=await cache.client.keys('airdeliver:provider:*:usage')
 entries=await cache.client.zrange(keys[0],0,-1)
 assert len(entries)==4 and all(s.endswith(':400') for s in entries)

@pytest.mark.asyncio
async def test_prior_other_worker_traffic_is_not_erased_to_make_next_turn_fit(real_cache):
 cache,_=real_cache
 async with shared_provider_slot('offline-chain-prior',[],{},1,client=cache.client,limit=7200) as r:
  r.observe(SimpleNamespace(usage=SimpleNamespace(total_tokens=5000)))
 _,messages,wire,output=(await chain('I need wired headphones'))[0]
 with pytest.raises(SharedProviderBudgetError):
  async with shared_provider_slot('offline-chain-prior',messages,wire,output,client=cache.client,limit=7200):pytest.fail('transport not allowed')
 entries=await cache.client.zrange((await cache.client.keys('airdeliver:provider:*:usage'))[0],0,-1)
 assert len(entries)==1 and entries[0].endswith(':5000')
