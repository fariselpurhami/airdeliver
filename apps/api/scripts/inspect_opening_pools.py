"""Owner-run read-only pool diagnostic. No models/providers or writes."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from redis.asyncio import Redis
from app.core.config import get_core_settings


async def inspect(user_id):
    settings=get_core_settings();seen=[];redis_status='unconfigured';client=None
    if settings.REDIS_URL:
        client=Redis.from_url(str(settings.REDIS_URL),socket_timeout=3,socket_connect_timeout=3)
        try:
            raw=await client.smembers(f'airdeliver:freshness:{user_id}')
            seen=[int(value) for value in raw if value and value.isdigit()]
            redis_status='read'
        except Exception:redis_status='unavailable_seen_exclusions_unknown'
        finally:await client.aclose()
    engine=create_async_engine(str(settings.DATABASE_URI))
    try:
        async with engine.connect() as db:
            async with db.begin():
                await db.execute(text('SET TRANSACTION READ ONLY'))
                result=await db.execute(text('''WITH catalog AS (
                    SELECT *, (is_active AND inventory>0 AND price>=0 AND currency ~ '^[A-Z]{3}$'
                        AND coalesce(attributes->>'_seed_dataset','') <> 'airdeliver-demo-v1'
                        AND sku NOT LIKE 'ADL-DEMO-v1-%' AND length(trim(name))>0) AS eligible,
                        NOT (id = ANY(CAST(:seen AS integer[]))) AS unseen
                    FROM products), pools AS (
                    (SELECT 'bestsellers' AS pool,eligible FROM catalog WHERE unseen ORDER BY rating DESC LIMIT 100)
                    UNION ALL (SELECT 'trending',eligible FROM catalog WHERE unseen ORDER BY rating DESC,inventory ASC LIMIT 100)
                    UNION ALL (SELECT 'deals_current_40',eligible FROM catalog WHERE unseen AND rating>=40 ORDER BY price ASC LIMIT 100)
                    UNION ALL (SELECT 'deals_proposed_4',eligible FROM catalog WHERE unseen AND rating>=4 ORDER BY price ASC LIMIT 100)
                    UNION ALL (SELECT 'personal_SQL_fallback_only',eligible FROM catalog WHERE unseen ORDER BY rating DESC LIMIT 20)
                    ) SELECT pool,count(*) AS raw_count,count(*) FILTER(WHERE eligible) AS eligible_count FROM pools GROUP BY pool ORDER BY pool'''),{'seen':seen})
                counts=[dict(row) for row in result.mappings()]
                totals=(await db.execute(text('''SELECT count(*) AS total,
                    count(*) FILTER(WHERE is_active) AS active,
                    count(*) FILTER(WHERE inventory>0) AS positive_stock,
                    count(*) FILTER(WHERE coalesce(attributes->>'_seed_dataset','')='airdeliver-demo-v1' OR sku LIKE 'ADL-DEMO-v1-%') AS demo,
                    min(rating) AS min_rating,max(rating) AS max_rating FROM products'''))).mappings().one()
                print(json.dumps({'user_id':user_id,'seen_count':len(seen),'redis_status':redis_status,
                    'catalog_counts':dict(totals),'pool_counts':counts,
                    'caveat':'Counts reproduce current pre-limit SQL pools only. Personal hybrid retrieval is not executed; its fallback count is not actual personal recall. Empty omitted pool means zero rows. No merchant availability proof.'},default=str))
    finally:await engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--user-id',type=int,required=True)
    args=parser.parse_args()
    if args.user_id<=0:parser.error('positive user ID required')
    try:asyncio.run(inspect(args.user_id))
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'message':'Read-only pool inspection failed; details withheld.'}))
        raise SystemExit(1) from None
