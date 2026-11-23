import json
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.services.recommendation_copy import factual_reasons,ground_recommendation_copy
from app.services.free_llm_service import FreeLLMService

P={'id':2,'name':'Shoe','category':'Mens_Shoes','price':100.68,'price_status':'listed','currency':'USD'}


@pytest.mark.parametrize('claim',['similar silhouette','premium design','compatible with all shoes',
    'Catalog-listed price: USD 1.','Catalog category: "other".',
    'Catalog-listed price: USD 100.68. Premium design.',
    'catalog-listed price: USD 100.68.','Catalog-listed price: USD 100.68!','Catalog-listed price: USD 100.68.\u200b'])
def test_unsupported_or_modified_claims_never_pass(claim):
    reasons,intro=ground_recommendation_copy([2],{'2':claim,'999':'free'},[P])
    assert reasons=={'2':factual_reasons(P,[P])[-1]}
    assert intro.startswith('1 catalog-listed option.')


@pytest.mark.parametrize('claim',factual_reasons(P))
def test_exact_truthful_template_preserved(claim):
    assert ground_recommendation_copy([2],{'2':claim},[P])[0]['2']==claim


@pytest.mark.parametrize('price',[None,0,-1,True,float('nan'),float('inf')])
def test_invalid_or_zero_price_not_claimed_as_free(price):
    p={**P,'price':price};out=json.dumps(factual_reasons(p))
    assert 'Catalog-listed price' not in out
    assert 'free' not in out.lower()


def test_unknown_status_currency_or_missing_fields_do_not_invent():
    assert factual_reasons({})==('Catalog-listed option.',)
    assert not any('price' in x for x in factual_reasons({**P,'price_status':'unknown'}))
    assert not any('price' in x for x in factual_reasons({**P,'currency':'US dollars'}))
    assert ground_recommendation_copy([],{},[])[1]=='No catalog-listed options were selected.'


@pytest.mark.parametrize('mode',['success','exception','empty'])
def test_actual_method_http_payload_covers_intro_reason_and_fallback(mode,monkeypatch):
    monkeypatch.setattr(FreeLLMService,'_instance',None);service=FreeLLMService()
    async def completion(**kw):
        if mode=='exception':raise RuntimeError('provider-private-payload')
        payload={'selected_ids':[] if mode=='empty' else [2],
                 'reasoning':{'2':'premium design and similar silhouette'},
                 'intro_message':'Guaranteed compatible delivery tomorrow!','confidence_score':.9}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    service._chat_completion=completion
    app=FastAPI()
    @app.get('/recommendation')
    async def route():return await service.filter_and_recommend('shoe',[P])
    with TestClient(app) as c:
        response=c.get('/recommendation');assert response.status_code==200
        row=response.json()
        assert row['selected_ids']==[2]
        assert row['reasoning']=={'2':factual_reasons(P,[P])[-1]}
        assert row['intro_message'].startswith('1 catalog-listed option.')
        for text in ('premium','silhouette','Guaranteed','tomorrow','private'):
            assert text not in response.text
