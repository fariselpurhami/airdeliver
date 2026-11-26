"""Intent task contrasts preserve current goal without changing product facts.

Controlled router/writer results test pipeline propagation, not model accuracy.
"""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.neural_core_service import NeuralCoreService,SessionMemory
from app.services.sales_response_service import SalesResponseService
from tests.test_sales_response_service import request

CONTRASTS=[
 ('specifications','Which material is listed for Atlas headphones?','evidence_and_unknowns','adaptive'),
 ('consultation','Would Atlas headphones work for calls if microphone details are missing?','evidence_and_unknowns','adaptive'),
 ('price_inquiry','What is the listed price for Atlas headphones?','listed_price_only','short'),
 ('negotiation','Can you lower the price for Atlas headphones?','explicit_concern_and_evidenced_options','adaptive'),
 ('objection','I am unsure whether Atlas headphones justify the price.','explicit_concern_and_evidenced_options','adaptive'),
 ('comparison','Compare the listed facts for Atlas headphones without inventing a winner.','evidence_and_unknowns','adaptive'),
]

@pytest.mark.asyncio
@pytest.mark.parametrize('task,question,strategy,shape',CONTRASTS)
async def test_same_card_different_explicit_goal_reaches_writer_and_review(task,question,strategy,shape):
 svc=NeuralCoreService(object(),object());svc.is_healthy=True
 memory=SessionMemory(user_name='test')
 memory.append_turn('Find Atlas headphones for calls.','Check the listed details.')
 svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas headphones','search_subject':'Atlas headphones','targets':[{'product_name':'Atlas headphones'}],'shopping_task':task}))
 decision=await svc._analyze_intent(question,memory)
 assert decision.shopping_task==task and decision.intent=='PRODUCT_SEARCH'
 seen=[]
 async def infer(messages):
  data=json.loads(messages[1]['content']);seen.append(data)
  if len(seen)==1:return json.dumps({'text':'The current listing does not verify the requested conclusion.','product_ids':[],'claims':[]})
  return json.dumps({'supported':True,'all_product_mentions_declared':True,'no_unsupported_commercial_claims':True,'fulfills_discovery_task':True})
 response=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(message=question,evidence={'shopping_task':decision.shopping_task,'exact_customer_question':question}))
 assert response.action is None and response.response_kind=='catalog_results'
 writer=seen[0];review=seen[1]['input']
 assert writer==review
 assert writer['customer_message']==question
 assert writer['request_evidence']['exact_customer_question']==question
 assert writer['request_evidence']['advisory_strategy']==strategy
 assert writer['request_evidence']['product_answer_shape']==shape
 assert writer['catalog_evidence']==review['catalog_evidence']

@pytest.mark.asyncio
async def test_current_question_is_not_replaced_by_a_prior_price_goal():
 memory=SessionMemory(user_name='test');memory.append_turn('What is the price of Atlas headphones?','The card has a listed price.')
 svc=NeuralCoreService(object(),object());svc.is_healthy=True
 svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas headphones','search_subject':'Atlas headphones','targets':[{'product_name':'Atlas headphones'}],'shopping_task':'consultation','sentiment':'URGENT','sentiment_evidence':'urgent','competitor_mentioned':'InventedStore','customer_signal':'desperate','advice_goal':'hesitation'}))
 question='Do Atlas headphones actually list a microphone?'
 d=await svc._analyze_intent(question,memory)
 assert d.shopping_task=='consultation'
 assert d.sentiment=='NEUTRAL' and d.sentiment_evidence is None
 assert d.competitor_mentioned is None and d.customer_signal is None
 assert d.advice_goal=='browse'

@pytest.mark.asyncio
@pytest.mark.parametrize('goal,task,question',[
 ('compare','comparison','Compare Atlas headphones with the listed alternative.'),
 ('understand','specifications','Help me understand the listed material for Atlas headphones.'),
])
async def test_nonemotional_goal_does_not_require_an_objection_signal(goal,task,question):
 svc=NeuralCoreService(object(),object());svc.is_healthy=True
 svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas headphones','search_subject':'Atlas headphones','targets':[{'product_name':'Atlas headphones'}],'shopping_task':task,'advice_goal':goal,'customer_signal':None}))
 d=await svc._analyze_intent(question,SessionMemory(user_name='test'))
 assert d.advice_goal==goal
 assert d.customer_signal is None and d.shopping_task==task

@pytest.mark.asyncio
async def test_neutral_goal_with_conflicting_task_is_not_retained_without_signal():
 svc=NeuralCoreService(object(),object());svc.is_healthy=True
 svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas headphones','search_subject':'Atlas headphones','shopping_task':'price_inquiry','advice_goal':'compare','customer_signal':None}))
 d=await svc._analyze_intent('What is the listed price for Atlas headphones?',SessionMemory(user_name='test'))
 assert d.advice_goal=='browse'
