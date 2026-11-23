"""Two real NLU turns, real Redis history, actual Groq SDK over local HTTP.
The scripted responder validates transport/context, not model understanding.
"""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from groq import AsyncGroq
from app.services.ai_nlu_service import AINLUService, RedisKeys
from app.services.free_llm_service import FreeLLMService
from tests.test_cart_persistence_outcomes import real_cache


@pytest.mark.asyncio
async def test_two_turn_product_followup_uses_server_history_over_real_transports(real_cache):
    cache,_ = real_cache
    captured=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captured.append(payload)
            system=payload['messages'][0]['content']
            user=payload['messages'][-1]['content']
            if 'Core Router' in system:
                content=json.dumps({'category':'PRICE_INQUIRY','is_chitchat':False,
                    'target_products':[{'product_name':'Atlas Headphones'}]})
            elif 'Search Query Optimizer' in system:
                data=json.loads(user)
                content='Atlas Headphones' if 'Atlas Headphones' in data['conversation_history'] else 'it'
            else:
                data=json.loads(user)
                content=f"{data['product']['name']} listed price is $49.00."
            body=json.dumps({'id':'local','object':'chat.completion','created':1,'model':'local',
                'choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}]}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    sdk=AsyncGroq(api_key='local-test-only',base_url=f'http://127.0.0.1:{server.server_port}/v1',max_retries=0)
    llm=FreeLLMService();llm._get_client=AsyncMock(return_value=sdk)
    service=AINLUService(object(),SimpleNamespace(),object(),cache,llm)
    service._handle_text_commands=AsyncMock(return_value=False)
    service._safe_web_search=AsyncMock(return_value='')
    service._get_user_dna=AsyncMock(return_value=SimpleNamespace(persona='explorer',tier='MEDIUM'))
    product={'id':7,'name':'Atlas Headphones','price':'49.00','inventory':8,'category':'audio'}
    service._execute_strategic_search=AsyncMock(return_value=[product])
    emitted=[]
    async def publish(channel,message): emitted.append((channel,json.loads(message)))
    cache.publish=publish
    try:
        # No frontend-supplied history. Both turns use the same authenticated id.
        await service.process_message({'user_id':17,'message':'Tell me about Atlas Headphones'})
        await service.process_message({'user_id':17,'message':'What about its price?'})
        answers=[p for _,p in emitted if p.get('products')]
        assert len(answers)==2
        assert answers[-1]['products'][0]['id']==7
        routing_calls=[p for p in captured if 'Core Router' in p['messages'][0]['content']]
        assert len(routing_calls)==2
        assert 'Atlas Headphones listed price' in routing_calls[1]['messages'][-1]['content']
        optimizer=[p for p in captured if 'Search Query Optimizer' in p['messages'][0]['content']][-1]
        assert 'Atlas Headphones' in json.loads(optimizer['messages'][-1]['content'])['conversation_history']
        answer_call=[p for p in captured if 'conversation_history' in p['messages'][-1]['content'] and 'Search Query Optimizer' not in p['messages'][0]['content']][-1]
        assert 'Atlas Headphones listed price' in json.loads(answer_call['messages'][-1]['content'])['conversation_history']
        assert all('Atlas Headphones' not in p['messages'][0]['content'] for p in captured)
        assert await service._get_conversation_context(18)==''
        assert 0 < await cache.client.ttl(RedisKeys.chat_history(17)) <= 86400
    finally:
        if service.tasks._tasks: await asyncio.gather(*service.tasks._tasks)
        await sdk.close();await asyncio.to_thread(server.shutdown);server.server_close();thread.join(timeout=2)
