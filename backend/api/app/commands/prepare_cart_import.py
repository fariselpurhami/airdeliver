"""Offline command, dry run default. Never connects to or changes Redis.

python -m app.commands.prepare_cart_import --bundle /private/cart-bundle.json
Explicit apply requires exact SHA256 and stopped-writers acknowledgement.
This command DOES NOT run a migration or enable canonical traffic.
"""
import argparse
import asyncio
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.core.config import get_core_settings
from app.services.cart_import_service import inspect_bundle,apply_bundle,bundle_digest

async def run(args):
    path=Path(args.bundle)
    if path.stat().st_size>20*1024*1024:raise ValueError('Import bundle exceeds20MiB')
    bundle=json.loads(path.read_text())
    engine=create_async_engine(get_core_settings().DATABASE_URI);sessions=async_sessionmaker(engine,expire_on_commit=False)
    try:
        async with sessions() as db:
            if args.apply_digest:
                if not args.writers_stopped:raise ValueError('Stop all writers before approved apply')
                result=await apply_bundle(db,bundle,args.apply_digest)
                await db.commit()
                print(json.dumps(result))
            else:
                report=await inspect_bundle(db,bundle)
                counts={}
                for row in report:counts[row['status']]=counts.get(row['status'],0)+1
                await db.rollback()
                # Never print names, addresses or cart contents to logs.
                print(json.dumps({'mode':'dry_run','digest':bundle_digest(bundle),'counts':counts,'writes':False}))
    finally:await engine.dispose()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',required=True)
    parser.add_argument('--apply-digest')
    parser.add_argument('--writers-stopped',action='store_true')
    asyncio.run(run(parser.parse_args()))
