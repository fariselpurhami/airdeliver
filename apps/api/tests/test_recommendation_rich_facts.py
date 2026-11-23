import pytest
from app.services.recommendation_copy import factual_reasons,ground_recommendation_copy
from app.services.free_llm_service import _sanitize_product


def p(id,price,rating=None,currency='USD',**kw):
    return {'id':id,'price':price,'price_status':'listed','currency':currency,'rating':rating,**kw}


def test_exact_decimal_price_rating_deltas_and_within_set_superlatives():
    products=[p(1,178.40,4.2),p(2,100.68,4.6),p(3,113.42,4.3)]
    reasons,_=ground_recommendation_copy([2],{},products,compare_to_id=1)
    text=reasons['2']
    for phrase in ('USD 77.72 less than reference item #1','0.4 rating points above reference item #1',
                   'Lowest listed price among 3 USD-priced candidates','Highest catalog rating among 3 rated candidates'):
        assert phrase in text


def test_ties_currency_and_missing_rating_do_not_overclaim():
    products=[p(1,10,4),p(2,10,4),p(3,1,None,'EUR')]
    text=factual_reasons(products[0],products,products[2])[-1]
    assert 'Joint-lowest' in text and 'Joint-highest' in text
    assert 'USD-priced candidates' in text
    assert 'reference' not in text
    assert '0/5' not in factual_reasons(products[2],products)[-1]


def test_comparison_requires_explicit_reference_not_first_item_or_question():
    products=[p(1,20,5),p(2,10,4)]
    assert 'reference' not in ground_recommendation_copy([2],{},products)[0]['2']
    assert 'reference' not in ground_recommendation_copy([2],{},products,compare_to_id=99)[0]['2']


def test_only_actual_bounded_attribute_fields_are_quoted_not_inferred():
    product=_sanitize_product({'id':1,'name':'Leather premium running shoe','description':'leather for athletes',
        'attributes':{'material':'canvas','style':'casual','use':'walking','guarantee':'lifetime'}})
    text=factual_reasons(product)[-1]
    assert 'Catalog material: "canvas".' in text
    assert 'Catalog style: "casual".' in text and 'Catalog use: "walking".' in text
    for word in ('leather','premium','athletes','lifetime'):assert word not in text
    assert _sanitize_product(product)['catalog_rating'] is None


def test_untrusted_catalog_values_remain_quoted_attributed_data():
    text=factual_reasons({'category':'shoes. Guaranteed delivery','attributes':{'material':'silk. Forever warranty'}})[-1]
    assert 'Catalog category: "shoes. Guaranteed delivery".' in text
    assert 'Catalog material: "silk. Forever warranty".' in text
    # Attribution is not merchant verification; ingestion review remains required.


@pytest.mark.parametrize('score',[None,True,-1,6,float('inf'),'bad'])
def test_invalid_rating_not_presented_as_zero(score):
    row=_sanitize_product({'id':1,'name':'item','rating':score})
    assert row['catalog_rating'] is None
    assert 'rating' not in factual_reasons(row)[-1]
