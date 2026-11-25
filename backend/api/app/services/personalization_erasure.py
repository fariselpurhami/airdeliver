"""Explicit reset, named stores, no account/cart/order deletion."""
import asyncio
from app.services.personalization_fence import key
from app.services.customer_memory_service import CustomerMemoryService
from app.core.catalog_contract import SPACES

class PersonalizationErasure:
    def __init__(self,db,cache,milvus):self.db=db;self.cache=cache;self.milvus=milvus

    async def erase(self,uid):
        import uuid
        token=uuid.uuid4().hex
        lock=key(uid)+':erase_lock'
        if not await self.cache.client.set(lock,token,nx=True,ex=120):raise RuntimeError('Another erase is running')
        try:
            async with asyncio.timeout(90):return await self._erase_locked(uid)
        finally:
            await self.cache.client.eval("if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) end return 0",1,lock,token)

    async def _erase_locked(self,uid):
        # Advance before deletion. Writes stamped before reset fail atomically.
        await self.cache.client.set(key(uid)+':reset_pending','1')
        await self.cache.client.incr(key(uid))
        await CustomerMemoryService(self.db).erase_preferences(uid)
        failures=[];deleted=0
        patterns=[f'ai:beh:u:{uid}:*',f'dna:profile:{uid}',f'dna:profile:{uid}:*',
          f'ai_session_v9:owner:{uid}:*',f'airdeliver:v2:session:{uid}:chat_history',
          f'airdeliver:v2:session:{uid}:seen_products',f'airdeliver:freshness:{uid}',f'airdeliver:freshness:{uid}:shown_at']
        try:
            for pattern in patterns:
                async for item in self.cache.client.scan_iter(match=pattern,count=100):
                    deleted+=await self.cache.client.delete(item)
        except asyncio.CancelledError:raise
        except Exception:failures.append('recent_context_and_derived_redis')
        collections=sorted({s.memory_collection for s in SPACES.values()}|{'airdeliver_memory_sota_v2'})
        for name in collections:
            try:
                if self.milvus is None:raise RuntimeError('Memory vector storage unavailable')
                exists=await asyncio.to_thread(self.milvus.has_collection,collection_name=name)
                if exists:
                    await asyncio.to_thread(self.milvus.delete,collection_name=name,filter=f'user_id == {uid}')
                    await asyncio.to_thread(self.milvus.flush,collection_name=name)
                    remaining=await asyncio.to_thread(self.milvus.query,collection_name=name,filter=f'user_id == {uid}',output_fields=['user_id'],limit=1,consistency_level='Strong')
                    if remaining:raise RuntimeError('Legacy memory erasure not yet visible')
            except asyncio.CancelledError:raise
            except Exception:failures.append(name)
        if not failures:
            await self.cache.client.incr(key(uid))
            await self.cache.client.delete(key(uid)+':reset_pending')
        return {'deleted':not failures,'learning_enabled':False,'incomplete_stores':failures,'redis_keys_deleted':deleted,
            'scope':'Saved preferences, shopping behavior, derived profiles, recent personalized context and shown history. Account, cart and orders unchanged.'}
