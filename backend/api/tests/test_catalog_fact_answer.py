"""Deterministic answers for narrow catalog-fact questions. Fail closed: unsure -> None (model path)."""
import asyncio
from types import SimpleNamespace
import pytest
from app.services.shopping_discovery import catalog_result, ShoppingBrief
from app.services.conversation.sales_response_service import SalesResponseService, SalesResponseRequest

def card(**kw):
    p={'id':7,'name':'Oak Desk','price':'59.00','currency':'USD','inventory':3,'is_active':True,'category':'Furniture','attributes':{'material':'oak','connectivity':'USB-C hub'}}
    p.update(kw);return catalog_result(SimpleNamespace(**p))

def ans(q,**kw):
    from app.services.conversation.catalog_fact_answer import catalog_fact_answer
    return catalog_fact_answer(q,[card(**kw)])

def test_price_question_is_answered_from_the_listed_price():
    t=ans('How much does the Oak Desk cost?')
    assert t and '59.00' in t and 'USD' in t and 'Oak Desk' in t

def test_price_question_without_a_listed_price_says_so():
    t=ans('What is the price of the Oak Desk?',price=None)
    assert t and 'does not list a price' in t and '59' not in t

def test_listed_attribute_is_quoted_exactly():
    t=ans('What is the listed material of the Oak Desk?')
    assert t and 'oak' in t

def test_unlisted_attribute_is_stated_as_unlisted_never_confirmed():
    for q,topic in [('Does the Oak Desk come with a warranty?','warranty'),('Does the Oak Desk come with free shipping?','free shipping'),
                    ('Does the Oak Desk come with next day delivery?','next day delivery'),('Is the Oak Desk waterproof?','waterproof')]:
        t=ans(q);assert t and f'does not list {topic}' in t and 'cannot confirm' in t,(q,t)

def test_listed_value_for_a_topic_falls_through_to_the_model():
    assert ans('Does the Oak Desk come with a warranty?',attributes={'warranty':'2 years'}) is None

@pytest.mark.parametrize('q',['Is the Oak Desk the best one you have?','Can you guarantee the Oak Desk arrives tomorrow?',
    'Is the Oak Desk cheaper than the Pine Desk?','How much does the Pine Desk cost?','Can I get a discount on the Oak Desk?',
    'How much does the Oak Desk cost and is it in stock?','price','Tell me about the Oak Desk'])
def test_anything_else_is_left_to_the_model(q):
    assert ans(q) is None

def test_needs_exactly_one_card():
    from app.services.conversation.catalog_fact_answer import catalog_fact_answer
    assert catalog_fact_answer('How much does the Oak Desk cost?',[card(),card(id=8,name='Pine Desk')]) is None
    assert catalog_fact_answer('How much does the Oak Desk cost?',[]) is None

def test_service_answers_without_calling_the_model_and_keeps_the_card():
    async def infer(m):raise AssertionError('model must not be called')
    svc=SalesResponseService(infer,provider_ready=True,timeout=5)
    r=asyncio.run(svc.respond(SalesResponseRequest(message='How much does the Oak Desk cost?',products=(card(),),brief=ShoppingBrief(),mode='catalog_results',intent='CATALOG_CONSULTATION',evidence={})))
    assert r.response_kind=='catalog_results' and '59.00' in r.text and [p.id for p in r.products]==[7]

def test_service_still_uses_the_model_for_open_questions():
    called=[]
    async def infer(m):called.append(1);raise RuntimeError('x')
    svc=SalesResponseService(infer,provider_ready=True,timeout=5)
    r=asyncio.run(svc.respond(SalesResponseRequest(message='Is the Oak Desk good for a small flat?',products=(card(),),brief=ShoppingBrief(),mode='catalog_results',intent='CATALOG_CONSULTATION',evidence={})))
    assert called and r.response_kind=='system_notice'
