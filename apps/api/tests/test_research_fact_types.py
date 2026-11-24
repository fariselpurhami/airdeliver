"""Actual extraction/review publication rejects coerced source identities."""
import json
from unittest.mock import AsyncMock
import pytest
from app.services.product_knowledge_service import answer_product_question

@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[
 ('source',True),('source',False),('source','0'),('source',0.0),
 ('label',False),('quote',123),('statement',True),('covered_targets',[123]),
])
async def test_actual_research_return_withholds_nonliteral_field_types(field,value):
    draft={'covered_targets':['Atlas'],'facts':[{'label':'Material','quote':'Atlas uses wood.','statement':'The source states wood.','source':0}]}
    if field=='covered_targets':draft[field]=value
    else:draft['facts'][0][field]=value
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps({'supported':True,'exact_model':True,'product_information_only':True})])
    lookup=AsyncMock(return_value=[{'url':'https://manufacturer.example/item','text':'Atlas uses wood.'},{'url':'https://manufacturer.example/other','text':'Atlas uses wood.'}])
    result=await answer_product_question(infer,'Atlas material',lookup=lookup,targets=('Atlas',))
    assert result.confidence==0 and result.products==[]
    assert 'invalid format' in result.text
    assert 'Source 1:' not in result.text and 'Source 2:' not in result.text
    infer.assert_awaited_once()

@pytest.mark.asyncio
async def test_actual_research_exact_integer_zero_and_nullable_statement_compatibility():
    infer=AsyncMock(side_effect=[json.dumps({'covered_targets':['Atlas'],'facts':[{'label':'Material','quote':'Atlas uses wood.','statement':None,'source':0}]}),json.dumps({'supported':True,'exact_model':True,'product_information_only':True})])
    result=await answer_product_question(infer,'Atlas material',lookup=AsyncMock(return_value=[{'url':'https://manufacturer.example/item','text':'Atlas uses wood.'}]),targets=('Atlas',))
    assert result.confidence>0 and 'https://manufacturer.example/item' in result.text
    assert infer.await_count==2
