"""Real loopback TCP/WebSocket transport, not a real ElevenLabs account or microphone."""
import asyncio
import base64
import json
import socket

import pytest
import uvicorn
import websockets
from fastapi import FastAPI,WebSocket
from app.services.ai_voice_service import AIVoiceOrchestrator,VoiceConfig
from app.services.cache_service import NoOpCacheClient


@pytest.mark.asyncio
async def test_real_duplex_websockets_pcm_and_provider_handshake(monkeypatch):
    got_audio=asyncio.Event();got_pong=asyncio.Event();got_tool=asyncio.Event();received={}
    pcm=b'\x01\x00\x02\x00'*160
    async def provider(ws):
        received['auth']=ws.request.headers.get('xi-api-key')
        await ws.send(json.dumps({'type':'ping','ping_event':{'event_id':42}}))
        await ws.send(json.dumps({'type':'client_tool_call','client_tool_call':{'tool_name':'unknown_read_only_test','tool_call_id':'call-1','parameters':{}}}))
        async for message in ws:
            data=json.loads(message)
            if data.get('type')=='pong' and data.get('event_id')==42:got_pong.set()
            if data.get('type')=='client_tool_result':
                received['tool']=data;got_tool.set()
            if 'user_audio_chunk' in data:
                received['audio']=base64.b64decode(data['user_audio_chunk'])
                # Current ElevenLabs wire envelope, not service-shaped top-level audio.
                await ws.send(json.dumps({'type':'audio','audio_event':{'audio_base_64':base64.b64encode(pcm).decode(),'event_id':1}}))
                await ws.send(json.dumps({'type':'agent_response','agent_response_event':{'agent_response':'Transport verified'}}))
                got_audio.set()
    async with websockets.serve(provider,'127.0.0.1',0) as upstream:
        port=upstream.sockets[0].getsockname()[1]
        monkeypatch.setattr(VoiceConfig,'ELEVENLABS_WS_URL_TEMPLATE',f'ws://127.0.0.1:{port}/{{agent_id}}')
        monkeypatch.setattr(VoiceConfig,'ELEVENLABS_AGENT_ID','loopback-agent')
        monkeypatch.setattr(VoiceConfig,'ELEVENLABS_API_KEY','loopback-not-a-real-secret')
        app=FastAPI()
        @app.websocket('/voice')
        async def route(ws:WebSocket):
            await AIVoiceOrchestrator(object(),object(),object(),NoOpCacheClient(),object()).process_voice_session(ws,'1')
        sock=socket.socket();sock.bind(('127.0.0.1',0));api_port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'))
        task=asyncio.create_task(server.serve(sockets=[sock]))
        try:
            async with asyncio.timeout(3):
                while not server.started:await asyncio.sleep(.01)
                async with websockets.connect(f'ws://127.0.0.1:{api_port}/voice') as client:
                    await client.send(pcm)
                    await asyncio.wait_for(got_audio.wait(),1)
                    assert await asyncio.wait_for(client.recv(),1)==pcm
                    assert json.loads(await asyncio.wait_for(client.recv(),1))['text']=='Transport verified'
                assert received['auth']=='loopback-not-a-real-secret'
                assert received['audio']==pcm
                await asyncio.wait_for(got_pong.wait(),1)
                await asyncio.wait_for(got_tool.wait(),1)
                assert received['tool']['tool_call_id']=='call-1'
                assert received['tool']['is_error'] is True
        finally:
            server.should_exit=True
            await asyncio.wait_for(task,3)
