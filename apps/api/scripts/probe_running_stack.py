"""Read-only dev acceptance preflight. No providers, model load, migration or writes.

Run inside an already-running API container. Prints counts/booleans only, never
credentials, customer identifiers or saved preferences. Does not test relevance,
consent mutations, real LLM answers, or embedding latency.
"""
import asyncio
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from app.core.config import get_core_settings
from app.db.session import AsyncSessionFactory


async def main(session_factory=AsyncSessionFactory, client_factory=None):
    import httpx
    started=time.perf_counter()
    result={'scope':'read-only preflight; no provider/model inference','checks':{}}
    async with session_factory() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        revision=(await db.execute(text('SELECT version_num FROM public.alembic_version'))).scalars().all()
        result['checks']['migration_revisions']=revision
        tables=(await db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('products','customer_memory_consent','customer_shopping_memory','customer_cart_state','cart_mutation_record')"))).scalars().all()
        result['checks']['tables']=sorted(tables)
        if 'products' in tables:
            result['checks']['product_count']=(await db.execute(text('SELECT count(*) FROM products'))).scalar_one()
        await db.rollback()
    result['checks']['memory_feature_enabled']=get_core_settings().CUSTOMER_MEMORY_ENABLED
    client_factory = client_factory or httpx.AsyncClient
    async with client_factory(timeout=httpx.Timeout(3.0,connect=2.0),trust_env=False) as client:
        for label,path in [('health','/api/v1/health'),('memory_unauthenticated','/api/v1/users/me/memory')]:
            step=time.perf_counter()
            try:
                async with asyncio.timeout(4.0):
                    response=await client.get('http://127.0.0.1:8000'+path)
                result['checks'][label+'_http_status']=response.status_code
            except (httpx.HTTPError, TimeoutError) as exc:
                result['checks'][label+'_error']=type(exc).__name__
            result['checks'][label+'_seconds']=round(time.perf_counter()-step,3)
    result['seconds']=round(time.perf_counter()-started,3)
    print(json.dumps(result,sort_keys=True))
    return result


if __name__=='__main__':
    asyncio.run(main())
