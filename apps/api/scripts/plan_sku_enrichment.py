"""Validate reviewed evidence and produce a read-only current-catalog merge plan."""
import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path
from app.schemas.sku_enrichment import Manifest, assert_importable, dry_run_plan

MAX_BYTES=8*1024*1024


def load_manifest(path):
    with Path(path).open('rb') as stream:raw=stream.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError('Manifest exceeds8MiB limit')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    data=json.loads(raw,object_pairs_hook=unique)
    # JSON parsing retains Decimal/datetime semantics through Pydantic JSON validation.
    manifest=Manifest.model_validate_json(json.dumps(data))
    return manifest,hashlib.sha256(raw).hexdigest()


async def plan_from_database(manifest):
    from sqlalchemy import text
    from app.db.session import AsyncSessionFactory
    skus=sorted({p.sku for p in manifest.products}|{r.target_sku for p in manifest.products for r in p.relations+p.compatibility})
    if len(skus)>20000:raise ValueError('Manifest exceeds20000 referenced SKUs')
    async with AsyncSessionFactory() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        await db.execute(text("SET LOCAL statement_timeout='5s'"))
        await db.execute(text("SET LOCAL lock_timeout='1s'"))
        rows=(await db.execute(text('SELECT sku, attributes FROM products WHERE sku=ANY(:skus) LIMIT 20001'),{'skus':skus})).mappings().all()
        await db.rollback()
    return dry_run_plan(manifest,{r['sku']:r['attributes'] for r in rows})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--schema-only',action='store_true',help='Check authoring shape, not import eligibility')
    args=parser.parse_args();logging.disable(logging.CRITICAL)
    try:
        manifest,digest=load_manifest(args.manifest)
        if not args.schema_only:assert_importable(manifest)
        result={'mode':'schema_only' if args.schema_only else 'validation_only','writes':0,
                'manifest_sha256':digest,'products':len(manifest.products)}
        if not args.schema_only and not args.validate_only:result={**asyncio.run(plan_from_database(manifest)),'manifest_sha256':digest}
        print(json.dumps(result,ensure_ascii=False))
    except Exception as exc:
        # Pydantic errors may contain raw source values. Never print the exception body.
        print(json.dumps({'accepted':False,'writes':0,'error_type':type(exc).__name__,
                          'detail':'Manifest rejected; inspect locally against schema and review requirements'}))
        raise SystemExit(2)


if __name__=='__main__':main()
