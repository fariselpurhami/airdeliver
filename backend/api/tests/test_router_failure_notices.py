import asyncio,json,logging
from unittest.mock import AsyncMock
from types import SimpleNamespace
import httpx,pytest
from groq import APIStatusError,APIConnectionError
from app.services.neural_core_service import NeuralCoreService,SessionMemory

@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['rate','auth','server','request','timeout','connection','schema','blank','notfound'])
async def test_actual_router_safe_cause_and_no_secret_leak(kind,caplog):
    service=object.__new__(NeuralCoreService);service.configuration_error=False;service.is_healthy=True
    statuses={'rate':429,'auth':401,'server':503,'request':400,'notfound':404}
    if kind in statuses:
        response=httpx.Response(statuses[kind],request=httpx.Request('POST','https://provider.example/private'))
        failure=APIStatusError('private key and account sentinel',response=response,body={'secret':'private payload sentinel'})
    elif kind=='timeout':failure=TimeoutError('private payload sentinel')
    elif kind=='connection':failure=APIConnectionError(request=httpx.Request('POST','https://provider.example/private'))
    elif kind=='blank':failure=ValueError('private payload sentinel')
    else:failure=None
    service._execute_llm_inference=AsyncMock(side_effect=failure) if failure else AsyncMock(return_value='{"intent":"INVALID"}')
    expected={'rate':'rate-limited','auth':'authenticate','server':'server error','request':'configuration error','timeout':'timed out','connection':'could not connect','schema':'invalid structured','blank':'could not validate','notfound':'model or endpoint configuration'}[kind]
    with caplog.at_level(logging.ERROR):decision=await service._analyze_intent('private customer sentinel',SessionMemory(user_name='test'))
    assert decision.intent=='SOCIAL_CHAT' and expected in decision.social_reply
    for secret in ['private key','private payload','private customer','provider.example']:
        assert secret not in decision.social_reply and secret not in caplog.text
    assert 'failure_category=' in caplog.text and 'error_type=' in caplog.text

@pytest.mark.asyncio
async def test_actual_specification_question_generated_contract_and_safe_field_diagnosis(caplog):
    service=object.__new__(NeuralCoreService);service.configuration_error=False;service.is_healthy=True
    seen=[]
    async def infer(messages):
        seen.append(messages)
        return json.dumps({'intent':'PRODUCT_SEARCH','shopping_task':'specifications','query':'Apple iPhone 17 Pro Max','search_subject':'Apple iPhone 17 Pro Max','targets':[{'product_name':'Apple iPhone 17 Pro Max'}]})
    service._execute_llm_inference=infer
    question='What are the specifications of Apple iPhone 17 Pro Max? Cite the sources you actually checked.'
    result=await service._analyze_intent(question,SessionMemory(user_name='test'))
    assert result.intent=='PRODUCT_SEARCH' and result.shopping_task=='specifications'
    assert 'authoritative response schema' in seen[0][0]['content']
    assert '$defs' not in seen[0][0]['content']
    assert 'Apple iPhone 17 Pro Max' not in seen[0][0]['content']
    service._execute_llm_inference=AsyncMock(return_value=json.dumps({'intent':'PRODUCT_SEARCH','quantity':None,'targets':None,'brief':None,'query':'private secret sentinel'}))
    with caplog.at_level(logging.ERROR):result=await service._analyze_intent(question,SessionMemory(user_name='test'))
    assert 'quantity:int_type' in caplog.text and 'targets:list_type' in caplog.text and 'brief:model_type' in caplog.text
    assert 'private secret sentinel' not in caplog.text and 'invalid structured' in result.social_reply
