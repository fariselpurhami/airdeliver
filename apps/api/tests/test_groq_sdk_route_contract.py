"""Actual SDK methods through fake transport, zero provider network traffic."""
import json
from pathlib import Path
import httpx
import pytest
from groq import AsyncGroq


@pytest.mark.asyncio
@pytest.mark.parametrize('base,expected_prefix',[
    ('https://api.groq.com','/openai/v1'),
    ('https://api.groq.com/openai/v1','/openai/v1/openai/v1'),
])
async def test_actual_sdk_resource_methods_build_single_or_double_prefix(base,expected_prefix):
    seen=[]
    def handler(request):
        seen.append(request)
        if request.method=='GET':
            return httpx.Response(200,json={'object':'list','data':[]})
        return httpx.Response(200,json={'id':'fake','object':'chat.completion','created':0,
            'model':'openai/gpt-oss-120b','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':'{}'}}]})
    async with AsyncGroq(api_key='synthetic-not-a-real-key',base_url=base,max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler),trust_env=False)) as client:
        await client.models.list()
        await client.chat.completions.create(model='openai/gpt-oss-120b',
            messages=[{'role':'user','content':'synthetic'}],max_tokens=1)
    assert [(r.method,str(r.url)) for r in seen]==[
        ('GET','https://api.groq.com'+expected_prefix+'/models'),
        ('POST','https://api.groq.com'+expected_prefix+'/chat/completions')]
    assert json.loads(seen[1].content)['max_tokens']==1


def test_all_acceptance_clients_use_origin_not_resource_prefix():
    root=Path(__file__).resolve().parents[1]/'scripts'
    for name in ['accept_dev_cart.py','reconcile_groq_acceptance.py','diagnose_groq_route.py']:
        source=(root/name).read_text()
        assert "base_url='https://api.groq.com/openai/v1'" not in source
        assert "acceptance_endpoint = 'https://api.groq.com/openai/v1'" not in source
