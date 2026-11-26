"""Controlled adapter contrasts, not provider understanding certification.

Characterizes remaining legacy metadata grounding gaps; no app fix claimed.
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.ai_nlu_service import GlobalCommerceIntentEngine
from app.services.neural_core_service import NeuralCoreService,SessionMemory

@pytest.mark.asyncio
@pytest.mark.parametrize('budget',[999,-1])
async def test_legacy_retains_model_budget_without_customer_amount_characterization(budget):
 infer=AsyncMock(return_value=json.dumps({'category':'SPECIFIC_SEARCH','target_products':[{'product_name':'Atlas'}],'is_chitchat':False,'budget_max':budget,'sentiment':'URGENT'}))
 result=await GlobalCommerceIntentEngine(SimpleNamespace(generate_response_strict=infer)).analyze_intent('Show Atlas headphones')
 # Known gap: these fields have no source-span validation in this adapter.
 assert result.budget_max==budget
 assert result.sentiment=='URGENT'
 assert result.target_products[0].product_name=='Atlas'

@pytest.mark.asyncio
async def test_support_drops_unbound_budget_and_sentiment_same_customer_question():
 svc=NeuralCoreService(object(),object());svc.is_healthy=True
 svc._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','query':'Atlas','search_subject':'Atlas','targets':[{'product_name':'Atlas'}],'sentiment':'URGENT','sentiment_evidence':'urgent','brief':{'budget':'under USD999','budget_max':'999','budget_currency':'USD'}}))
 decision=await svc._analyze_intent('Show Atlas headphones',SessionMemory(user_name='test'))
 assert decision.sentiment=='NEUTRAL'
 assert decision.brief.budget is None and decision.brief.budget_max is None

@pytest.mark.asyncio
async def test_legacy_removes_unbound_competitor_but_retains_ungrounded_emotional_label():
 infer=AsyncMock(return_value=json.dumps({'category':'OBJECTION','target_products':[{'product_name':'Atlas'}],'is_chitchat':False,'competitor_mentioned':'InventedStore','sentiment':'FRUSTRATED'}))
 result=await GlobalCommerceIntentEngine(SimpleNamespace(generate_response_strict=infer)).analyze_intent('Show Atlas headphones')
 assert result.competitor_mentioned is None
 assert result.sentiment=='FRUSTRATED'
