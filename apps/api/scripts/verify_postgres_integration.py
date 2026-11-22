"""Migrate and test only an explicitly named disposable PostgreSQL 19 database.

Run from apps/api: poetry run python scripts/verify_postgres_integration.py
TEST_POSTGRES_DSN must use postgresql+asyncpg and database airdeliver_test_*.
Never point this test helper at a production database.
"""
import asyncio
import os
from pathlib import Path
import runpy
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


def main():
    dsn = os.environ.get('TEST_POSTGRES_DSN', '')
    if not dsn:
        raise SystemExit('TEST_POSTGRES_DSN must name a disposable PostgreSQL 19 test database')
    url = make_url(dsn)
    if url.drivername != 'postgresql+asyncpg' or not (url.database or '').startswith('airdeliver_test_'):
        raise SystemExit('Refusing to migrate: expected postgresql+asyncpg and database airdeliver_test_*')
    api = Path(__file__).resolve().parents[1]
    os.chdir(api)
    sys.path.insert(0, str(api))
    os.environ['DATABASE_URI'] = dsn
    runpy.run_path(str(api / 'tests/conftest.py'))

    async def check_server():
        engine = create_async_engine(dsn)
        try:
            async with engine.begin() as conn:
                version = int((await conn.execute(text('SHOW server_version_num'))).scalar_one())
                if version // 10000 != 19:
                    raise RuntimeError('Integration CI requires PostgreSQL major version 19')
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
                version = (await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))).scalar_one()
                if version != '0.8.7':
                    raise RuntimeError('Integration CI requires pgvector 0.8.7')
                distance = (await conn.execute(text("SELECT '[1,2]'::vector <-> '[4,6]'::vector"))).scalar_one()
                if distance != 5.0:
                    raise RuntimeError('pgvector distance smoke test failed')
        finally:
            await engine.dispose()
    asyncio.run(check_server())
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(api / 'alembic.ini')), 'head')
    import pytest
    return pytest.main(sys.argv[1:] or ['tests/', '-q'])


if __name__ == '__main__':
    raise SystemExit(main())
