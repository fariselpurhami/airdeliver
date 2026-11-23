"""Real loopback voice socket and PostgreSQL revocation, no media provider."""
import asyncio
import json
import os
import socket
from uuid import uuid4
import pytest
import uvicorn
import websockets
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.api import deps
from app.api.v1.endpoints import ai_ordering
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.services.cache_service import get_cache_from_request
from app.services.password_reset_service import issue_reset,consume_reset

pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
@pytest.mark.parametrize("watcher_outage",[False,True])
async def test_real_voice_socket_closes_after_independent_database_reset(monkeypatch,watcher_outage):
 import app.db.session as dbmodule
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN'])
 sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  user=User(email=uuid4().hex+'@example.com',hashed_password=get_password_hash('old-socket-password'))
  db.add(user);await db.commit();uid,email=user.id,user.email
  _,link=await issue_reset(db,email,'socket-'+uuid4().hex,settings.model_copy(update={'PASSWORD_RESET_WEB_ORIGIN':'https://shop.example.test'}))
 class Cache:
  store={'ws_ticket:socket-test':json.dumps({'user_id':uid,'ver':0})}
  async def get(self,key):return self.store.get(key)
  async def set(self,key,value,ttl=None):self.store[key]=value
  async def delete(self,key):self.store.pop(key,None)
 cache=Cache()
 class Orchestrator:
  def __init__(self,**kwargs):pass
  async def process_voice_session(self,ws,user_id):
   await ws.accept()
   try:
    while True:await ws.receive_bytes()
   except Exception:pass
 async def dbdep():
  async with sessions() as db:yield db
 app=FastAPI();app.include_router(ai_ordering.router)
 app.dependency_overrides[deps.get_async_session]=dbdep
 app.dependency_overrides[deps.get_ai_commerce_engine]=lambda:object()
 app.dependency_overrides[deps.get_llm_service]=lambda:object()
 app.dependency_overrides[ai_ordering.get_rabbitmq_service]=lambda:object()
 app.dependency_overrides[get_cache_from_request]=lambda:cache
 monkeypatch.setattr(ai_ordering,'AIVoiceOrchestrator',Orchestrator)
 monkeypatch.setattr(dbmodule,'AsyncSessionFactory',sessions)
 sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'))
 task=asyncio.create_task(server.serve(sockets=[sock]))
 try:
  async with asyncio.timeout(12):
   while not server.started:await asyncio.sleep(.01)
   async with websockets.connect(f'ws://127.0.0.1:{port}/voice-stream?ticket=socket-test') as ws:
    if watcher_outage:
     def unavailable():raise OSError('fixture database outage')
     monkeypatch.setattr(dbmodule,'AsyncSessionFactory',unavailable)
    else:
     async with sessions() as db:assert await consume_reset(db,link.split('#token=')[1],'new-socket-password')
    with pytest.raises(websockets.exceptions.ConnectionClosed) as exc:
     await ws.recv()
    assert exc.value.rcvd.code==(1011 if watcher_outage else 1008)
 finally:
  server.should_exit=True
  await asyncio.wait_for(task,3)
  await engine.dispose()
 assert f'voice_session_lock:{uid}' not in cache.store
