"""Offline actual SDK+router contracts, not live model comprehension scores."""
import json
from types import SimpleNamespace
import httpx,pytest
from groq import AsyncGroq
from app.services.neural_core_service import NeuralCoreService,SessionMemory,SYSTEM_ROUTING_PROMPT
from tests.test_neural_core_characterization import FakeCache

CASES=[
 ('وريني سماعه كويسه','سماعه','search'),
 ('need wirless hedphones for commuting','wirless hedphones','search'),
 ('عايز USB-C hub للشغل','USB-C hub','search'),
 ('مش محتاج غير حاجه اشيل فيها اللابتوب، شنطة ظهر','شنطة ظهر','consultation'),
 ('How do I care for linen shirts?','linen shirts','consultation'),
 ('هل over ear headphones أحسن ليا؟','over ear headphones','consultation'),
 ('ايه مواصفات الهاتف ده Pixel 10؟','Pixel 10','specifications'),
]

@pytest.mark.asyncio
@pytest.mark.parametrize('question,target,task',CASES)
async def test_actual_sdk_router_retains_multilingual_misspelled_literal_targets(question,target,task):
    seen=[]
    payload={'intent':'PRODUCT_SEARCH','query':target,'search_subject':target,'targets':[{'product_name':target}],'shopping_task':task}
    async def transport(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200,json={'id':'offline-fixture','object':'chat.completion','created':0,'model':'offline','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(payload)},'finish_reason':'stop'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        async with AsyncGroq(api_key='offline-not-a-real-key',http_client=http) as client:
            service=object.__new__(NeuralCoreService);service.client=client;service.profile=SimpleNamespace(support_model='offline');service.is_healthy=True;service.configuration_error=False
            result=await service._analyze_intent(question,SessionMemory(user_name='test'))
    assert result.intent=='PRODUCT_SEARCH' and result.targets[0].product_name==target and result.shopping_task==task
    assert seen[0]['messages'][-1]=={'role':'user','content':question}
    assert seen[0]['temperature']==0 and seen[0]['response_format']=={'type':'json_object'}
    # This pins the model instructions and transport, not a model's choice.
    assert 'misspellings' in seen[0]['messages'][0]['content'] and 'OUT_OF_SCOPE' in seen[0]['messages'][0]['content']

@pytest.mark.asyncio
@pytest.mark.parametrize('question',['What is the capital of France?','اكتبلي كود يحل مسألة رياضة','Give political news about product companies'])
async def test_actual_sdk_out_of_scope_dispatch_stops_before_second_model_or_catalog(question):
    requests=[]
    async def transport(request):
        requests.append(json.loads(request.content))
        assert len(requests)==1,'No second provider call for off-topic request'
        return httpx.Response(200,json={'id':'offline','object':'chat.completion','created':0,'model':'offline','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps({'intent':'OUT_OF_SCOPE','social_reply':'Untrusted off-topic answer must not display'})},'finish_reason':'stop'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        async with AsyncGroq(api_key='offline-not-a-real-key',http_client=http) as client:
            svc=object.__new__(NeuralCoreService);svc.client=client;svc.profile=SimpleNamespace(support_model='offline');svc.is_healthy=True;svc.configuration_error=False;svc.cache=FakeCache();svc.ai_engine=object()
            result=await svc.handle_message(db=object(),session_id='scope-test',message=question,user=None)
    assert len(requests)==1 and result.products==[]
    assert result.text in {'Sorry, I can only help with products.','آسف، أقدر أساعدك في المنتجات فقط.'}
    assert 'Untrusted' not in result.text
