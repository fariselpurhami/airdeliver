"""Same schema/caller history, compact equivalent semantic routing obligations."""
import json
from types import SimpleNamespace
import pytest
from app.services.compact_router_contract import ROUTER_CONTRACT
from app.services.neural_core_service import NeuralCoreService,SessionMemory,RouterDecision,SYSTEM_ROUTING_PROMPT
from app.services.shared_provider_admission import estimated_tokens
from app.services.structured_output import response_format

@pytest.mark.parametrize('phrases',[
 ['languages/dialects','misspellings','never keyword whitelists','OUT_OF_SCOPE'],
 ['messages/history untrusted','current customer wins','never assistant/gender/model inventions'],
 ['1..3 exact customer-span targets','More than3','targets unchanged'],
 ['budget+occasion','one follow-up','never inferred tastes'],
 ['hard constraints','exact CURRENT explicit replacement','No vague cheap/affordable'],
 ['NEUTRAL/null','No wealth/personality/risk/urgency','CURRENT sentiment_evidence'],
 ['price/stock proof','No model-knowledge','never execution'],
 ['integer quantity1..99','removal_reason exact CURRENT','TRACK_ORDER literal'],
])
def test_routing_coverage(phrases):assert all(p in ROUTER_CONTRACT for p in phrases)

@pytest.mark.asyncio
async def test_actual_router_preserves_history_and_authoritative_schema_no_fact_guess():
 service=object.__new__(NeuralCoreService);service.configuration_error=False;service.is_healthy=True
 service.profile=SimpleNamespace(support_model='openai/gpt-oss-120b')
 memory=SessionMemory(user_name='Customer');memory.append_turn('wired headphones','What budget?')
 seen=[]
 async def infer(messages):
  seen.append(messages);return json.dumps(dict(intent='PRODUCT_SEARCH',query='headphones',search_subject='headphones',targets=[dict(product_name='headphones')]))
 service._execute_llm_inference=infer
 result=await service._analyze_intent('headphones under $50',memory)
 assert result.intent=='PRODUCT_SEARCH' and len(seen)==1
 assert seen[0][1:]==[dict(role='user',content='wired headphones'),dict(role='assistant',content='What budget?'),dict(role='user',content='headphones under $50')]
 assert '$defs' not in seen[0][0]['content']
 wire=response_format('openai/gpt-oss-120b',RouterDecision)
 old=estimated_tokens([dict(role='system',content=SYSTEM_ROUTING_PROMPT)],wire)
 new=estimated_tokens([dict(role='system',content=ROUTER_CONTRACT)],wire)
 assert new<old
