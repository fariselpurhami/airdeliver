"""Read-only exact current opening classification. No provider/model/write."""
import argparse,asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from app.db.session import AsyncSessionFactory
from app.core.config import get_core_settings
from app.services.opening_catalog_status import opening_catalog_status

async def main(user_id):
    from redis.asyncio import Redis
    settings=get_core_settings();client=None;recent=set();state='unconfigured'
    if settings.REDIS_URL:
        client=Redis.from_url(str(settings.REDIS_URL),socket_timeout=3,socket_connect_timeout=3)
        try:
            import time
            values=await client.zrangebyscore(f'airdeliver:freshness:{user_id}:shown_at',time.time()-settings.OPENING_PRODUCT_COOLDOWN_SECONDS,'+inf')
            recent={int(x) for x in values};state='read'
        except Exception:state='unavailable_cooldown_unknown'
        finally:await client.aclose()
    async with AsyncSessionFactory() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        status=await opening_catalog_status(db,recent)
        await db.rollback()
    print(json.dumps({'scope':'read-only current SQL eligibility and timestamp cooldown; no providers/models/writes',
        'cooldown_state':state,'cooldown_seconds':settings.OPENING_PRODUCT_COOLDOWN_SECONDS,
        'counts':status,'caveat':'If cooldown_state is not read, real_fresh is provisional and cooldown cannot be ruled out. Counts do not verify merchant availability or model copy.'},sort_keys=True))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--user-id',type=int,required=True);args=parser.parse_args()
    if args.user_id<=0:parser.error('positive userID required')
    try:asyncio.run(main(args.user_id))
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'message':'Read-only inspection failed; no writes performed.'}));raise SystemExit(1) from None
