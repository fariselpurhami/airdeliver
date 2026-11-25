import os
import shutil
import socket
import subprocess
import time
from types import SimpleNamespace
import pytest
from redis import Redis
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import build_limiter, install_rate_limiting


def application(instance):
    app=FastAPI();install_rate_limiting(app,instance)
    app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
    @app.get('/plain')
    async def plain(request:Request):return {'ok':True}
    @app.get('/decorated')
    @instance.limit('2/minute')
    async def decorated(request:Request):return {'ok':True}
    @app.get('/health')
    @instance.exempt
    async def health(request:Request):return {'ok':True}
    return app


def settings(url=None,default='2/minute'):
    return SimpleNamespace(USE_REDIS=bool(url),REDIS_URL=url,RATE_LIMIT_DEFAULT=default)


def test_default_limits_decorated_limits_and_health_exemption():
    app=application(build_limiter(settings()))
    with TestClient(app) as c:
        assert [c.get('/plain').status_code for _ in range(3)]==[200,200,429]
        assert [c.get('/decorated').status_code for _ in range(3)]==[200,200,429]
        assert all(c.get('/health').status_code==200 for _ in range(5))


def test_forwarded_header_cannot_change_client_key():
    instance=build_limiter(settings());app=application(instance)
    with TestClient(app,client=('203.0.113.1',123)) as c:
        assert c.get('/plain',headers={'x-forwarded-for':'198.51.100.1'}).status_code==200
        assert c.get('/plain',headers={'x-forwarded-for':'198.51.100.2'}).status_code==200
        assert c.get('/plain',headers={'x-forwarded-for':'198.51.100.3'}).status_code==429
    with TestClient(app,client=('203.0.113.2',123)) as c:
        assert c.get('/plain').status_code==200


@pytest.fixture
def redis_server(tmp_path):
    binary=os.environ.get('TEST_REDIS_SERVER_BIN') or shutil.which('redis-server')
    if not binary:pytest.skip('Disposable Redis binary required')
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    with (tmp_path/'redis.log').open('w') as log:
        p=subprocess.Popen([binary,'--bind','127.0.0.1','--port',str(port),'--save','','--appendonly','no','--dir',str(tmp_path)],stdout=log,stderr=log)
        raw=Redis(host='127.0.0.1',port=port,socket_connect_timeout=.1,socket_timeout=.1)
        try:
            for _ in range(100):
                try:
                    if raw.ping():break
                except Exception:time.sleep(.02)
            else:raise RuntimeError('Disposable Redis not ready')
            yield f'redis://127.0.0.1:{port}/0',p
        finally:
            raw.close()
            if p.poll() is None:p.terminate();p.wait(3)


def test_actual_redis_shares_quota_between_independent_limiters(redis_server):
    url,_=redis_server
    a,b=build_limiter(settings(url)),build_limiter(settings(url))
    with TestClient(application(a)) as first,TestClient(application(b)) as second:
        assert first.get('/plain').status_code==200
        assert second.get('/plain').status_code==200
        assert first.get('/plain').status_code==429
        assert second.get('/plain').status_code==429
        # A new independent client still has its own quota.
        with TestClient(application(b),client=('198.51.100.7',10)) as other:
            assert other.get('/plain').status_code==200


def test_window_recovers_without_restart(redis_server):
    url,_=redis_server;instance=build_limiter(settings(url,'1/second'))
    with TestClient(application(instance)) as c:
        assert c.get('/plain').status_code==200
        assert c.get('/plain').status_code==429
        time.sleep(1.1)
        assert c.get('/plain').status_code==200


def test_redis_outage_fails_closed_without_credential_echo(redis_server):
    url,p=redis_server;instance=build_limiter(settings(url));app=application(instance)
    p.terminate();p.wait(3)
    with TestClient(app,raise_server_exceptions=False) as c:
        for path in ('/plain','/decorated'):
            response=c.get(path)
            assert response.status_code==503
            assert response.json()=={'detail':'Rate limit storage unavailable'}
            assert url not in response.text
        assert c.get('/health').status_code==200
