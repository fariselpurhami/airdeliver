# apps/api/tests/test_llm_grounding.py
"""
Programmatic grounding tests: LLM-selected product IDs must be verified
against the retrieved candidate set before they can reach the user.

Covers FreeLLMService.filter_and_recommend with a stubbed chat completion.
No network or Groq access.
"""
import json

import pytest

from app.services.free_llm_service import FreeLLMService


def _products():
    return [
        {"id": 1, "name": "AeroPhone 12", "price": "899.00", "rating": 4.5,
         "category": "phones", "brand": "aero", "description": "flagship phone"},
        {"id": 2, "name": "Zephyr Laptop 14", "price": "1299.00", "rating": 4.7,
         "category": "laptops", "brand": "zephyr", "description": "light laptop"},
        {"id": 3, "name": "Nimbus Buds", "price": "149.00", "rating": 4.2,
         "category": "audio", "brand": "nimbus", "description": "wireless earbuds"},
        {"id": 4, "name": "Titan Watch", "price": "349.00", "rating": 4.4,
         "category": "wearables", "brand": "titan", "description": "smart watch"},
    ]


def _completion_with(payload: dict):
    class _Msg:
        content = json.dumps(payload)

    class _Choice:
        message = _Msg()

    class _Completion:
        choices = [_Choice()]

    return _Completion()


def _service_returning(payload: dict) -> FreeLLMService:
    svc = FreeLLMService()

    async def fake_chat_completion(**kwargs):
        return _completion_with(payload)

    svc._chat_completion = fake_chat_completion
    return svc


@pytest.mark.anyio
async def test_valid_selection_passes_through():
    svc = _service_returning({
        "selected_ids": [1, 2],
        "reasoning": {"1": "great phone", "2": "light laptop"},
        "intro_message": "Top picks for you.",
        "confidence_score": 0.9,
    })
    result = await svc.filter_and_recommend("phone", _products())
    assert result.selected_ids == [1, 2]
    assert set(result.reasoning)=={"1","2"}
    assert 'Catalog category: "phones".' in result.reasoning["1"]


@pytest.mark.anyio
async def test_hallucinated_ids_are_dropped():
    svc = _service_returning({
        "selected_ids": [1, 999, 1000],
        "reasoning": {"1": "great phone", "999": "ghost", "1000": "ghost2"},
        "intro_message": "Top picks.",
        "confidence_score": 0.9,
    })
    result = await svc.filter_and_recommend("phone", _products())
    # 999/1000 were never in the candidate set: dropped before reaching the user
    assert result.selected_ids == [1]
    # reasoning contract preserved: keys match surviving selections
    assert 'Catalog category: "phones".' in result.reasoning["1"]
    assert set(result.reasoning)=={"1"}


@pytest.mark.anyio
async def test_all_hallucinated_ids_fall_back_to_real_products():
    svc = _service_returning({
        "selected_ids": [777, 888, 999],
        "reasoning": {"777": "ghost"},
        "intro_message": "Top picks.",
        "confidence_score": 0.9,
    })
    result = await svc.filter_and_recommend("phone", _products())
    # grounding empties the selection -> existing fallback to top real candidates
    assert result.selected_ids != []
    assert set(result.selected_ids) <= {1, 2, 3, 4}


@pytest.mark.anyio
async def test_empty_selection_uses_fallback():
    svc = _service_returning({
        "selected_ids": [],
        "reasoning": {},
        "intro_message": "Nothing.",
        "confidence_score": 0.1,
    })
    result = await svc.filter_and_recommend("phone", _products())
    assert result.selected_ids  # non-empty, drawn from real candidates
    assert set(result.selected_ids) <= {1, 2, 3, 4}


@pytest.mark.anyio
async def test_no_products_returns_none():
    svc = _service_returning({})
    assert await svc.filter_and_recommend("phone", []) is None


@pytest.mark.anyio
async def test_valid_selected_ids_do_not_allow_reasoning_for_unselected_or_invented_products():
    svc=_service_returning({'selected_ids':[1], 'reasoning':{'1':'Listed selection','2':'Not selected','999':'Not in catalog'},
        'intro_message':'Listed option','confidence_score':0.5})
    result=await svc.filter_and_recommend('phone',_products())
    assert result.selected_ids==[1]
    assert set(result.reasoning)=={'1'}
    assert 'Not selected' not in str(result.reasoning)
    assert 'Listed selection' not in str(result.reasoning)


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity',float('inf')])
def test_catalog_numeric_sanitization_never_emits_nonfinite_json_numbers(value):
    from app.services.free_llm_service import _sanitize_product
    import math
    product=_sanitize_product({'id':float('inf'),'name':'Corrupt numeric row','price':value,'rating':value})
    assert product['id']==0
    assert product['price'] is None and product['price_status']=='unknown'
    assert math.isfinite(product['rating'])
    json.dumps(product,allow_nan=False)


@pytest.mark.parametrize('price',[None,'',True,-1,'not-a-price'])
def test_unknown_catalog_price_stays_unknown_across_repeated_sanitization(price):
    from app.services.free_llm_service import _sanitize_product
    product=_sanitize_product({'id':7,'name':'Unpriced item','price':price})
    assert product['price'] is None and product['price_status']=='unknown'
    assert _sanitize_product(product)['price'] is None


def test_actual_listed_zero_is_distinct_from_unknown():
    from app.services.free_llm_service import _sanitize_product
    product=_sanitize_product({'id':7,'name':'Listed zero','price':'0.00'})
    assert product['price']==0.0 and product['price_status']=='listed'


@pytest.mark.anyio
async def test_model_receives_unknown_price_not_zero_fallback():
    svc=_service_returning({'selected_ids':[7],'reasoning':{'7':'Listed item'}})
    captured=[]
    async def completion(**kwargs):
        captured.append(kwargs)
        return _completion_with({'selected_ids':[7],'reasoning':{'7':'Listed item'}})
    svc._chat_completion=completion
    await svc.filter_and_recommend('shoes',[{'id':7,'name':'Shoes'}])
    data=json.loads(captured[0]['messages'][1]['content'])
    assert data['products'][0]['price'] is None
    assert data['products'][0]['price_status']=='unknown'


@pytest.mark.anyio
async def test_mixed_unknown_prices_keep_lifestyle_selection_operational():
    svc=_service_returning({})
    result=await svc._legacy_generate_lifestyle_matrix([{'id':7,'name':'Unpriced shoes'}, {'id':8,'name':'Listed socks','price':'5.00'}])
    assert len(result)==4
    assert any(row['product']['price'] is None for row in result)
    assert not any('Great price' in row['text'] for row in result)
