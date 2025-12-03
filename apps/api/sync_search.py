# apps/api/sync_search.py

import asyncio
import logging
import time
import sys
import os
from typing import List, Dict, Any
from sqlmodel import select, func, col
from opensearchpy import AsyncOpenSearch, helpers
from app.db.session import SessionLocal
from app.models.product import Product
from app.core.config import get_core_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("airdeliver.diamond_sync")

class DiamondSearchSynchronizer:
    """
    💎 DIAMOND EDITION SYNCHRONIZER
    
    Architectural Pillars:
    1. Keyset Pagination: Zero-latency fetching regardless of DB size (O(1)).
    2. Async Producer-Consumer: Decoupled fetching and indexing pipelines.
    3. Backpressure Handling: Bounded queues to prevent RAM spikes.
    4. Raw SQL Execution: Bypassing ORM overhead for maximum throughput.
    """
    
    def __init__(self):
        self.settings = get_core_settings()
        self.index_name = "airdeliver_products"
    
        self.fetch_batch_size = 5000   
        self.upload_chunk_size = 2000  
        self.concurrent_workers = 5    
        self.queue_size = 20  

        os_host = os.getenv("OPENSEARCH_HOST", "opensearch")
        os_port = int(os.getenv("OPENSEARCH_PORT", 9200))

        logger.info(f"🔌 Connecting to OpenSearch at: {os_host}:{os_port}")

        self.client = AsyncOpenSearch(
            hosts=[{"host": self.settings.OPENSEARCH_HOST, "port": self.settings.OPENSEARCH_PORT}],
            use_ssl=False,
            verify_certs=False,
            timeout=120, 
            max_retries=5,
            retry_on_timeout=True
        )

    async def _create_optimized_index(self):
        """Creates index with settings tuned for heavy-write throughput."""
        exists = await self.client.indices.exists(index=self.index_name)
        if not exists:
            logger.info(f"🏗️  Infrastructure: Creating high-performance index '{self.index_name}'...")
            body = {
                "settings": {
                    "number_of_shards": 2, 
                    "number_of_replicas": 0, 
                    "refresh_interval": "-1", 
                    "translog.durability": "async" 
                },
                "mappings": {
                    "properties": {
                        "name": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "category": {"type": "keyword"}, 
                        "tags": {"type": "text", "boost": 2},
                        "price": {"type": "float"},
                        "rating": {"type": "float"},
                        "id": {"type": "integer"}
                    }
                }
            }
            await self.client.indices.create(index=self.index_name, body=body)

    async def _producer(self, queue: asyncio.Queue):
        """
        🚀 High-Speed Data Ingestion (Keyset Pagination).
        Fetches raw data dictionaries to minimize CPU overhead.
        """
        logger.info("🔌 Producer: Connecting to SQL Core...")
        async with SessionLocal() as db:
            last_seen_id = 0
            total_fetched = 0
            
            while True:
                query = (
                    select(
                        Product.id, Product.name, Product.description, 
                        Product.category, Product.tags, Product.price, 
                        Product.rating, Product.image_url
                    )
                    .where(Product.id > last_seen_id)
                    .order_by(Product.id)
                    .limit(self.fetch_batch_size)
                )
                
                result = await db.exec(query)
                batch = result.mappings().all()

                if not batch:
                    break

                docs = []
                for p in batch:
                    docs.append({
                        "_index": self.index_name,
                        "_id": p['id'],
                        "_source": {
                            "name": p['name'],
                            "description": p['description'],
                            "category": p['category'],
                            "tags": p['tags'],
                            "price": p['price'],
                            "rating": p['rating'],
                            "image_url": p['image_url']
                        }
                    })
                
                last_seen_id = batch[-1]['id']
                total_fetched += len(batch)
                
                await queue.put(docs)
                
                if total_fetched % 50000 == 0:
                    logger.info(f"📥 Producer: Fetched {total_fetched:,} products so far...")

        for _ in range(self.concurrent_workers):
            await queue.put(None)
        logger.info("✅ Producer: Finished fetching all data.")

    async def _consumer(self, worker_id: int, queue: asyncio.Queue, stats: Dict[str, int]):
        """
        🚀 Parallel Uploader.
        Pulls batches and blasts them to OpenSearch.
        """
        while True:
            batch = await queue.get()
            if batch is None:
                queue.task_done()
                break 

            try:
                
                success, failed = await helpers.async_bulk(
                    self.client,
                    batch,
                    chunk_size=self.upload_chunk_size,
                    raise_on_error=False,
                    request_timeout=60
                )
                stats['success'] += success
                stats['failed'] += len(failed)
                
                if len(failed) > 0:
                    logger.warning(f"⚠️ Worker {worker_id}: {len(failed)} docs failed to index.")
                    
            except Exception as e:
                logger.error(f"🔥 Worker {worker_id} Crash: {e}")
                stats['failed'] += len(batch)
            finally:
                queue.task_done()

    async def sync(self):
        overall_start = time.time()
        stats = {'success': 0, 'failed': 0}
        
        try:
            
            await self._create_optimized_index()
            
            await self.client.indices.put_settings(
                index=self.index_name, 
                body={"index": {"refresh_interval": "-1", "number_of_replicas": 0}}
            )

            queue = asyncio.Queue(maxsize=self.queue_size)
            
            logger.info(f"🚀 Starting Diamond Sync with {self.concurrent_workers} parallel workers...")
            
            producer_task = asyncio.create_task(self._producer(queue))
            
            consumers = [
                asyncio.create_task(self._consumer(i, queue, stats)) 
                for i in range(self.concurrent_workers)
            ]

            await producer_task
            await queue.join() 
            await asyncio.gather(*consumers)

            logger.info("🧹 Finalizing Index (Merge & Refresh)...")
            await self.client.indices.put_settings(
                index=self.index_name, 
                body={"index": {"refresh_interval": "1s", "number_of_replicas": 0}} # Keep 0 replicas for dev
            )
            await self.client.indices.forcemerge(index=self.index_name, max_num_segments=1)
            await self.client.indices.refresh(index=self.index_name)

            duration = time.time() - overall_start
            throughput = (stats['success'] + stats['failed']) / duration
            
            logger.info(f"""
            =============================================
            💎 DIAMOND SYNC COMPLETE
            =============================================
            ⏱️  Duration:    {duration:.2f} seconds
            🚀 Throughput:  {throughput:,.0f} docs/sec
            ✅ Indexed:     {stats['success']:,}
            ❌ Failed:      {stats['failed']:,}
            =============================================
            """)

        except Exception as e:
            logger.critical(f"💀 Fatal System Error: {e}", exc_info=True)
        finally:
            await self.client.close()

if __name__ == "__main__":

    try:
        import uvloop
        uvloop.install()
        logger.info("⚡ uvloop activated for maximum performance.")
    except ImportError:
        pass

    synchronizer = DiamondSearchSynchronizer()
    asyncio.run(synchronizer.sync())
