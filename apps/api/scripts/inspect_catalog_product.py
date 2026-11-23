"""Owner-run, read-only, bounded catalog provenance inspection.

Never prints credentials, product attributes beyond the demo marker, customer
records or arbitrary table content. PostgreSQL enforces read-only transaction.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


async def inspect(name: str, engine=None, *, contains=False):
    owned=engine is None
    engine=engine or create_async_engine(str(settings.DATABASE_URI))
    try:
        async with engine.connect() as connection:
            async with connection.begin():
                await connection.execute(text('SET TRANSACTION READ ONLY'))
                rows=(await connection.execute(text('''SELECT id,sku,name,price,currency,inventory,is_active,
                    attributes->>'_seed_dataset' AS seed_dataset,updated_at
                    FROM products WHERE CASE WHEN :contains THEN lower(name) LIKE lower(:pattern) ESCAPE '!' ELSE lower(name)=lower(:name) END ORDER BY id LIMIT 10'''),{'name':name,'contains':contains,'pattern':'%'+name.replace('!','!!').replace('%','!%').replace('_','!_')+'%'})).mappings().all()
                print(json.dumps({'rows':[dict(row) for row in rows],'limit':10,
                    'meaning':'Local catalog only, not merchant availability proof.'},default=str))
    finally:
        if owned:await engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--contains',action='store_true',help='Literal substring, not wildcard search')
    args=parser.parse_args()
    if not args.name.strip() or len(args.name)>255:parser.error('name must be 1..255 characters')
    try:asyncio.run(inspect(args.name,contains=args.contains))
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'message':'Read-only inspection failed; connection details withheld.'}))
        raise SystemExit(1) from None
