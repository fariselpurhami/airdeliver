"""Owner-controlled reversible quarantine, never deletes product/order/history rows.

Default plan is read-only. Apply requires a restore-verified manifest, and every
current marked row must still match. Rollback refuses concurrent row changes.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

MARKED="(coalesce(attributes->>'_seed_dataset','')='airdeliver-demo-v1' OR sku LIKE 'ADL-DEMO-v1-%')"
COLUMNS='id,sku,is_active,updated_at'


async def snapshot(connection,lock=False):
    result=await connection.execute(text(f'SELECT {COLUMNS} FROM products WHERE {MARKED} ORDER BY id'+(' FOR UPDATE' if lock else '')))
    return [dict(row) for row in result.mappings().all()]


def encoded(rows):return json.dumps(rows,default=str,sort_keys=True)


async def make_plan(engine,restored_engine,archive,manifest):
    archive=Path(archive);manifest=Path(manifest)
    if not archive.is_file() or archive.stat().st_size==0:raise ValueError('Readable backup archive required')
    if manifest.exists():raise ValueError('Refusing to overwrite manifest')
    async with engine.connect() as connection,restored_engine.connect() as restored:
        await connection.execute(text('SET TRANSACTION READ ONLY'))
        await restored.execute(text('SET TRANSACTION READ ONLY'))
        identity=(await connection.execute(text('SELECT current_database()'))).scalar_one()
        restored_identity=(await restored.execute(text('SELECT current_database()'))).scalar_one()
        if identity==restored_identity:raise ValueError('Restore verification requires a different database name')
        rows=await snapshot(connection);verified=await snapshot(restored)
        count=(await connection.execute(text('SELECT count(*) FROM products'))).scalar_one()
        verified_count=(await restored.execute(text('SELECT count(*) FROM products'))).scalar_one()
        if encoded(rows)!=encoded(verified) or count!=verified_count:raise ValueError('Restored product snapshot does not match current source')
        data={'version':1,'database':identity,'restore_database':restored_identity,'backup_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),'before':rows,'product_count':count}
        fd=os.open(manifest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(json.dumps(data,default=str,indent=2)+'\n')
    return len(rows)


async def change(engine,manifest,*,rollback=False):
    path=Path(manifest);data=json.loads(path.read_text());receipt=Path(str(path)+'.applied.json')
    if data.get('version')!=1 or not data.get('backup_sha256') or not data.get('restore_database'):raise ValueError('Verified manifest required')
    if rollback:
        after=json.loads(receipt.read_text())['after']
    elif receipt.exists():raise ValueError('Already applied; inspect receipt')
    async with engine.begin() as connection:
        identity=(await connection.execute(text('SELECT current_database()'))).scalar_one()
        if identity!=data['database']:raise ValueError('Wrong database')
        current=await snapshot(connection,lock=True)
        if encoded(current)!=encoded(after if rollback else data['before']):raise ValueError('Catalog changed; no rows changed')
        for row in data['before']:
            await connection.execute(text('UPDATE products SET is_active=:active,updated_at=clock_timestamp() WHERE id=:id AND sku=:sku'),{'active':row['is_active'] if rollback else False,'id':row['id'],'sku':row['sku']})
        result=await snapshot(connection)
        # Receipt is prepared before commit; if commit fails it is uncertain,
        # never automatically replay. Current state must be inspected first.
        target=Path(str(path)+('.rollback.json' if rollback else '.applied.json'))
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(json.dumps({'after':result,'commit':'must_verify_current_state'},default=str,indent=2)+'\n')
    return len(result)


async def main(args):
    from app.core.config import settings
    engine=create_async_engine(str(settings.DATABASE_URI))
    try:
        if args.mode=='plan':
            uri=os.environ.get('AIRDELIVER_RESTORED_DATABASE_URI')
            if not uri:raise ValueError('Isolated restored database connection required')
            restored=create_async_engine(uri)
            try:count=await make_plan(engine,restored,args.archive,args.manifest)
            finally:await restored.dispose()
        else:count=await change(engine,args.manifest,rollback=args.mode=='rollback')
        print(json.dumps({'mode':args.mode,'marked_rows':count,'deleted_rows':0,'message':'Inspect current state and retain manifest/receipts; no automatic replay after uncertainty.'}))
    finally:await engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['plan','apply','rollback']);parser.add_argument('--manifest',required=True);parser.add_argument('--archive')
    args=parser.parse_args()
    try:asyncio.run(main(args))
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'message':'Quarantine operation not confirmed. Inspect receipt/current state before retrying. Connection details withheld.'}));raise SystemExit(1) from None
