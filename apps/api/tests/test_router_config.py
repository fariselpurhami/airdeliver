import logging
import pytest
import httpx
from groq import AsyncGroq
from app.core.router_config import get_router_config,log_router_configuration,RouterConfigurationError
from app.core.logging_config import JsonFormatter


def test_router_default_and_explicit_override():
    assert get_router_config({}).model=='openai/gpt-oss-120b'
    assert get_router_config({'GROQ_SUPPORT_MODEL':'enterprise-model'}).model=='enterprise-model'
    assert get_router_config({}).base_url=='https://api.groq.com'

@pytest.mark.parametrize('url',['https://api.groq.com/openai/v1','https://name:PRIVATE@api.groq.com','https://api.groq.com?token=PRIVATE','http://api.groq.com',''])
def test_reject_bad_native_base_without_logging_supplied_url(url,caplog):
    with pytest.raises(RouterConfigurationError):get_router_config({'GROQ_BASE_URL':url})
    with caplog.at_level(logging.INFO):assert log_router_configuration({'GROQ_BASE_URL':url}) is None
    assert 'PRIVATE' not in caplog.text
    assert 'invalid_native_sdk_base_url' in caplog.text

@pytest.mark.asyncio
async def test_actual_sdk_builds_one_native_path_without_network():
    seen=[]
    async def handle(request):
        seen.append(str(request.url))
        return httpx.Response(200,json={'id':'local','object':'chat.completion','created':0,'model':'test','choices':[{'index':0,'message':{'role':'assistant','content':'{}'},'finish_reason':'stop'}]})
    config=get_router_config({})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client=AsyncGroq(api_key='test-only',base_url=config.base_url,http_client=http)
        await client.chat.completions.create(model=config.model,messages=[{'role':'user','content':'local contract'}])
    assert seen==['https://api.groq.com/openai/v1/chat/completions']

@pytest.mark.asyncio
async def test_provider_404_reports_configuration_not_transient_retry(monkeypatch):
    from app.services.neural_core_service import NeuralCoreService,SessionMemory
    from groq import NotFoundError
    service=object.__new__(NeuralCoreService);service.is_healthy=True
    async def fail(messages):
        raise NotFoundError('PRIVATE_PROVIDER_BODY',response=httpx.Response(404,request=httpx.Request('POST','https://api.groq.com')),body=None)
    service._execute_llm_inference=fail
    result=await service._analyze_intent('local test',SessionMemory(user_name='F'))
    assert 'configuration problem' in result.social_reply
    assert 'PRIVATE' not in result.social_reply
