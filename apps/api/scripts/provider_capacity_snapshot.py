"""Usage: python -m scripts.provider_capacity_snapshot --model MODEL

Reads numeric Redis state only. No network request to any model/provider.
"""
import argparse
import asyncio
import json
from app.core.config import get_core_settings
from app.services.provider_capacity_snapshot import capacity_snapshot

async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,choices=['openai/gpt-oss-120b','openai/gpt-oss-20b'])
    args=parser.parse_args();settings=get_core_settings()
    if not settings.REDIS_URL:raise SystemExit('Shared ledger unavailable; no capacity claim can be made.')
    from redis.asyncio import Redis
    from redis.asyncio.retry import Retry
    from redis.backoff import NoBackoff
    async with Redis.from_url(settings.REDIS_URL,decode_responses=True,socket_timeout=1,socket_connect_timeout=1,retry=Retry(NoBackoff(),0)) as client:
        result=await capacity_snapshot(client,args.model,settings.PROVIDER_TPM_BUDGET)
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':asyncio.run(main())
