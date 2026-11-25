from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.shopping_discovery import ShoppingBrief,catalog_result
from app.services.target_constraint_scope import assign_target_scope

def card(specs,name='Product',category='electronics'):
    return catalog_result(SimpleNamespace(id=1,name=name,category=category,sku='real',price=20,currency='USD',is_active=True,inventory=2,attributes=specs))

@pytest.mark.parametrize('feature,specs,expected',[
    ('OLED',{'OLED':False},False),('OLED',{'OLED':'unknown'},False),('OLED',{'OLED':True},True),
    ('OLED',{'display':'not OLED'},False),('OLED',{'display':'OLED or LCD'},False),
    ('OLED',{'display':'OLED'},True),('USB-C',{'connector':'USB - C'},True),
    ('red',{'color':'infrared'},False),('blue metal',{'color':'blue','material':'metal'},False),
    ('120cm',{'width':'120 cm'},True),('120cm',{'width':'1.2m'},False),
    ('waterproof',{'waterproof':'not supported'},False),('wireless',{'connection':'wired'},False),
])
def test_noncapacity_evidence_is_literal_isolated_and_affirmative(feature,specs,expected):
    assert ShoppingBrief(required_features=[feature]).permits(card(specs)) is expected

@pytest.mark.parametrize('budget',['NaN','Infinity','-1','bad'])
def test_malformed_saved_budget_cannot_raise_or_admit_cards(budget):
    assert not ShoppingBrief(budget_max=budget,budget_currency='USD').permits(card({}))

@pytest.mark.asyncio
@pytest.mark.parametrize('targets,features',[(['desk','DESK'],[]),('desk',[]),(['desk'],['x'*129]),(['desk'],[None]),(['desk']*4,[])])
async def test_invalid_scope_input_rejected_before_provider(targets,features):
    infer=AsyncMock()
    with pytest.raises(ValueError):await assign_target_scope(infer,'desk',targets,features)
    infer.assert_not_awaited()
