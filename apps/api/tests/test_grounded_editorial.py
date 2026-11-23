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
    content,reason=await service._generate_dynamic_row_copy('Personalized',PRODUCTS,'Good morning search','elite premium')
    assert 'silk' not in content+reason and 'premium' not in content+reason and 'Good morning' not in content+reason
    assert 'search' not in content or 'No search preferences' in content
    if mode=='valid':assert content=='Catalog item: "Belt".'
    else:assert 'Catalog category' in reason


def test_greeting_does_not_infer_search_time_or_personalization():
    service=object.__new__(AINLUService)
    text=service._get_time_aware_greeting('HIGH')
    assert 'morning' not in text and 'premium' not in text and 'current search' not in text
