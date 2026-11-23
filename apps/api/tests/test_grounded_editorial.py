import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.grounded_editorial import claim_catalog,validate_editorial,factual_editorial_fallback
from app.services.ai_nlu_service import AINLUService

PRODUCTS=[{'id':1,'name':'Belt','category':'Accessories','price':100.,'price_status':'listed','currency':'USD',
           'attributes':{'material':'leather'}},{'id':2,'name':'Sweater','category':'Clothing','price':150.,'price_status':'listed','currency':'USD'}]


def valid():
    return {'content':[{'claim_id':'1:name','connector':'space'}],
            'reason':[{'claim_id':'1:fact:0','connector':'space'},{'claim_id':'2:name','connector':'meanwhile'}]}


def test_editorial_order_choices_render_only_item_bound_claims():
    claims=claim_catalog(PRODUCTS);content,reason=validate_editorial(valid(),claims)
    assert content=='Catalog item: "Belt".' and 'Sweater' in reason
    assert 'Meanwhile,' in reason


@pytest.mark.parametrize('payload',[
 {'content':'premium silk elegance','reason':'iconic heels'},
 {'content':[{'claim_id':'999:name','connector':'space'}],'reason':[]},
 {'content':[{'claim_id':'1:name','connector':'<script>'}],'reason':[]},
 {'content':[{'claim_id':'1:name','connector':'space','text':'premium'}],'reason':[]},
])
def test_labeled_unsupported_free_text_cross_item_or_html_rejected(payload):
    with pytest.raises(ValueError):validate_editorial(payload,claim_catalog(PRODUCTS))


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['valid','invented','failure'])
async def test_actual_row_copy_method_safe_generation_and_fallback(mode):
    async def generate(**kwargs):
        assert 'allowed_claims' in kwargs['prompt'] and 'Belt' in kwargs['prompt']
        if mode=='failure':raise RuntimeError('offline')
        return json.dumps(valid() if mode=='valid' else {'content':'silk elegance','reason':'premium heels'})
    service=object.__new__(AINLUService);service.llm_service=SimpleNamespace(generate_response=generate)
    content,reason=await service._legacy_generate_dynamic_row_copy('Personalized',PRODUCTS,'Good morning search','elite premium')
    assert 'silk' not in content+reason and 'premium' not in content+reason and 'Good morning' not in content+reason
    assert 'search' not in content or 'No search preferences' in content
    assert content=='A curated selection of Accessories and Clothing, brought together in one considered edit.'
    assert 'clothing' in reason and 'accessories' in reason
    assert 'USD' not in content+reason and 'priced' not in content+reason


def test_greeting_does_not_infer_search_time_or_personalization():
    service=object.__new__(AINLUService)
    text=service._get_time_aware_greeting('HIGH')
    assert 'morning' not in text and 'premium' not in text and 'current search' not in text


def test_opening_editorial_is_card_bound_without_price_or_invented_claims():
    from app.services.grounded_editorial import opening_editorial
    products=[{**PRODUCTS[0],'brand':'Gucci'},{**PRODUCTS[1],'brand':'Patagonia'}]
    content,reason=opening_editorial(products)
    assert 'Gucci and Patagonia' in content and 'clothing' in reason and 'accessories' in reason
    for unsupported in ('Flagship','precision-calibrated','skin','silk','heel','your standards','trending','bestseller'):
        assert unsupported not in content+reason
    changed=opening_editorial([products[1]])
    assert 'Gucci' not in str(changed) and 'Belt' not in str(changed)
    unknown=opening_editorial([{**PRODUCTS[0],'price_status':'unknown'}])
    assert 'USD' not in str(unknown)


@pytest.mark.parametrize('category,expected', [('Clothing','already wear'),('Accessories','finishing touch'),('Electronics','how you would use it')])
def test_opening_guidance_follows_displayed_category_and_ignores_prices(category,expected):
    from app.services.grounded_editorial import opening_editorial
    product={**PRODUCTS[0],'category':category}
    copy=opening_editorial([product])
    assert expected in copy[1]
    assert copy==opening_editorial([{**product,'price':99999,'currency':'EUR','rating':1}])
    assert 'USD' not in str(copy) and '99999' not in str(copy)
    if category!='Clothing':
        assert 'clothing' not in copy[1]


def test_opening_mixed_categories_do_not_invent_an_outfit():
    from app.services.grounded_editorial import opening_editorial
    content,reason=opening_editorial([PRODUCTS[0],{**PRODUCTS[1],'category':'Electronics'}])
    assert 'Different categories' in reason
    assert 'look' not in reason and 'outfit' not in reason
