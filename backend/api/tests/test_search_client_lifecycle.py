"""CAP-12 actual HTTP connection/client lifecycle plus bounded SDK retries."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from aiohttp import web
from app.services import ai_commerce_engine as module


@pytest.mark.asyncio
async def test_real_opensearch_http_response_and_client_close_on_generator_exit():
    calls=[]
    async def root(request):
        calls.append(request.path)
        return web.json_response({'name':'disposable','version':{'number':'2.19.1','distribution':'opensearch'},'tagline':'The OpenSearch Project: https://opensearch.org/'})
    app=web.Application();app.router.add_get('/',root)
    runner=web.AppRunner(app);await runner.setup()
    site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1]
    settings=SimpleNamespace(OPENSEARCH_HOST='127.0.0.1',OPENSEARCH_PORT=port,
        OPENSEARCH_USE_SSL=False,OPENSEARCH_VERIFY_CERTS=False,OPENSEARCH_USER=None,OPENSEARCH_PASS=None)
    generator=module.get_opensearch_client(settings)
    client=await anext(generator)
    try:
        assert (await client.info())['name']=='disposable'
        connection=client.transport.get_connection()
        assert connection.session is not None and not connection.session.closed
        session=connection.session
        await generator.aclose()
        assert session.closed and calls==['/']
    finally:
        await generator.aclose();await runner.cleanup()


def test_milvus_transient_retry_preserves_token_timeout_and_returns_exact_client(monkeypatch):
    calls=[];sleeps=[];expected=object()
    def build(**kwargs):
        calls.append(kwargs)
        if len(calls)<3:raise ConnectionError('temporarily unavailable')
        return expected
    monkeypatch.setattr(module,'_build_milvus_client',build)
    monkeypatch.setattr(module.time,'sleep',sleeps.append)
    settings=SimpleNamespace(MILVUS_URI='http://localhost:19530',MILVUS_TOKEN=SimpleNamespace(get_secret_value=lambda:'controlled-test-token'))
    result=module.connect_milvus_with_retry(settings,policy=module.MilvusRetryPolicy(max_attempts=3,jitter_ratio=0,connect_timeout_seconds=.5))
    assert result is expected and sleeps==[1,2]
    assert calls==[{'uri':'http://localhost:19530','token':'controlled-test-token','timeout':.5}]*3


@pytest.mark.parametrize('error,expected_calls',[(ValueError('invalid auth'),1),(ConnectionError('connection refused'),3)])
def test_milvus_terminal_and_exhausted_failures_do_not_return_client(monkeypatch,error,expected_calls):
    build=Mock(side_effect=error);monkeypatch.setattr(module,'_build_milvus_client',build)
    monkeypatch.setattr(module.time,'sleep',lambda _:None)
    with pytest.raises(module.MilvusConnectionError):
        module.connect_milvus_with_retry(SimpleNamespace(MILVUS_URI='http://localhost:19530',MILVUS_TOKEN=None),
            policy=module.MilvusRetryPolicy(max_attempts=3,jitter_ratio=0))
    assert build.call_count==expected_calls
