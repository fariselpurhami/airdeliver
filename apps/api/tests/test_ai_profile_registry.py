from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from groq import AsyncGroq
from app.core.ai_profile import get_ai_profile, AIProfile, UnsupportedAIProfile
from app.services.ai_adapters import GroqAdapter, LocalRetrievalAdapter, ElevenLabsConversationAdapter


def test_current_profile_preserves_defaults_and_role_overrides():
    p=get_ai_profile({})
    assert (p.brain_model,p.reflex_model,p.support_model,p.vision_model)==(
        'openai/gpt-oss-120b','openai/gpt-oss-20b','llama-3.3-70b-versatile','qwen/qwen3.8-27b')
    p=get_ai_profile({'GROQ_BRAIN_MODEL':'brain','GROQ_MODEL':'reflex','GROQ_SUPPORT_MODEL':'support','GROQ_VISION_MODEL':'vision'})
    assert (p.brain_model,p.reflex_model,p.support_model,p.vision_model)==('brain','reflex','support','vision')


@pytest.mark.parametrize('change',[{'name':'missing'}, {'text_provider':'other'},
    {'voice_provider':'other'}, {'text_retrieval_dimension':384}, {'image_retrieval_model':'other'},
    {'brain_model':'bad model with whitespace'}])
def test_unsupported_profiles_providers_models_and_index_contract_rejected(change):
    if 'name' in change:
        with pytest.raises(UnsupportedAIProfile):get_ai_profile({'AI_PROFILE':change['name']})
    else:
        with pytest.raises(UnsupportedAIProfile):replace(get_ai_profile({}),**change)


def test_unknown_stt_capability_does_not_claim_independent_adapter():
    with pytest.raises(UnsupportedAIProfile):get_ai_profile({}).require('standalone_stt')


@pytest.mark.asyncio
async def test_groq_adapter_uses_actual_sdk_route_json_and_caller_timeout(monkeypatch):
    monkeypatch.delenv('GROQ_BASE_URL',raising=False)
    seen=[]
    def response(request):
        seen.append(request)
        return httpx.Response(200,json={'id':'fake','object':'chat.completion','created':0,
            'model':'openai/gpt-oss-120b','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':'{}'}}]})
    transport=httpx.MockTransport(response)
    adapter=GroqAdapter(get_ai_profile({}),AsyncGroq)
    async with adapter.create_client(api_key='synthetic-only',timeout=2,
            http_client=httpx.AsyncClient(transport=transport)) as client:
        assert client.max_retries==0
        result=await client.chat.completions.create(model=adapter.profile.brain_model,
            messages=[{'role':'user','content':'synthetic'}],response_format={'type':'json_object'},max_tokens=1)
        assert result.choices[0].message.content=='{}'
    assert str(seen[0].url)=='https://api.groq.com/openai/v1/chat/completions'
    assert seen[0].extensions['timeout']['read']==2


def test_local_adapter_preserves_current_model_revision_and_options():
    seen=[]
    def factory(name,**kw):seen.append((name,kw));return 'component'
    adapter=LocalRetrievalAdapter(get_ai_profile({}))
    assert adapter.create_text_encoder(factory,revision='pinned',trust_remote_code=False)=='component'
    assert adapter.create_image_component(factory,revision='vision',trust_remote_code=True)=='component'
    assert seen==[(adapter.profile.text_retrieval_model,{'revision':'pinned','trust_remote_code':False}),
                  (adapter.profile.image_retrieval_model,{'revision':'vision','trust_remote_code':True})]


@pytest.mark.asyncio
async def test_voice_adapter_preserves_wire_options_and_propagates_failure():
    adapter=ElevenLabsConversationAdapter(get_ai_profile({}))
    connector=AsyncMock(return_value='socket')
    assert await adapter.connect(connector,'wss://example.invalid/session',headers={'xi-api-key':'synthetic'},ping_interval=20,ping_timeout=20)=='socket'
    connector.assert_awaited_once_with('wss://example.invalid/session',additional_headers={'xi-api-key':'synthetic'},ping_interval=20,ping_timeout=20)
    connector.side_effect=ConnectionError('controlled')
    with pytest.raises(ConnectionError):await adapter.connect(connector,'wss://example.invalid',headers={},ping_interval=20,ping_timeout=20)
