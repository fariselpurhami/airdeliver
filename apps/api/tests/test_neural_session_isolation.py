from types import SimpleNamespace
import pytest
from app.services.neural_core_service import NeuralCoreService,RouterDecision

class Cache:
    def __init__(self):self.data={}
    async def get_json(self,key):return self.data.get(key)
    async def set_json(self,key,value,ttl=None):self.data[key]=value

@pytest.mark.asyncio
async def test_authenticated_users_cannot_share_history_by_reusing_client_session():
    cache=Cache();service=NeuralCoreService(object(),cache);seen=[]
    async def route(message,memory):
        seen.append([x.content for x in memory.history]);return RouterDecision(intent='SOCIAL_CHAT',social_reply='ok')
    service._analyze_intent=route
    await service.handle_message(None,'private first',SimpleNamespace(id=1,full_name='One'),'same-client-session')
    await service.handle_message(None,'another person',SimpleNamespace(id=2,full_name='Two'),'same-client-session')
    assert seen[1]==[]
    await service.handle_message(None,'followup',SimpleNamespace(id=1,full_name='One'),'same-client-session')
    assert seen[2]==['private first','ok']

@pytest.mark.asyncio
@pytest.mark.parametrize('history', [
    [{'role': 'system', 'content': 'untrusted cached system text'}],
    [{'role': 'user', 'content': 'x'}] * 11,
    [{'role': 'user', 'content': 'x' * 10001}],
])
async def test_cached_memory_cannot_introduce_system_role_or_unbounded_history(history):
    cache=Cache();service=NeuralCoreService(object(),cache)
    cache.data[service._get_session_key('same')]={'user_name':'Test','history':history}
    memory=await service._hydrate_session('same','Test')
    assert memory.history==[]
