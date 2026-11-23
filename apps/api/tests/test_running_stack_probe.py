from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from sqlalchemy import text
from scripts.probe_running_stack import main
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
async def test_preflight_read_only_queries_and_no_auth_headers(memory_db,capsys):
    sessions,_=memory_db; seen=[]
    def respond(request):
        seen.append(request)
        assert 'authorization' not in request.headers
        return httpx.Response(200 if request.url.path.endswith('/health') else 401)
    async with sessions() as db:
        expected=(await db.execute(text('SELECT version_num FROM public.alembic_version'))).scalars().all()
    result=await main(sessions,lambda **kw:httpx.AsyncClient(transport=httpx.MockTransport(respond),**kw))
    assert result['checks']['migration_revisions']==expected
    assert result['checks']['memory_unauthenticated_http_status']==401
    assert len(seen)==2 and result['checks']['product_count']>=0
    output=capsys.readouterr().out
    assert 'password' not in output.lower() and 'token' not in output.lower()
