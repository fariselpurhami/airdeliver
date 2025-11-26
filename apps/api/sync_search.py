# apps/api/sync_search.py

import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, Any
from sqlmodel import select, func
from opensearchpy import AsyncOpenSearch, helpers
from app.db.session import SessionLocal
from app.models.product import Product
from app.core.config import get_core_settings

# --- Enterprise Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("airdeliver.sync")

class SearchSynchronizer:
    """
    Diamond Standard Synchronizer.
    Features:
    - Streaming Bulk Upload (Low Memory Footprint).
    - Explicit Index Mapping (Better Search Relevance).
    - Performance Tuning (Refresh Interval Optimization).
    """
    def __init__(self):
        self.settings = get_core_settings()
        self.index_name = "airdeliver_products"
        self.batch_size = 2000 # Process 2000 items at a time
        self.client = AsyncOpenSearch(
            hosts=[{"host": self.settings.OPENSEARCH_HOST, "port": self.settings.OPENSEARCH_PORT}],
            use_ssl=False,
            verify_certs=False,
            timeout=60, # Increased timeout for bulk ops
            max_retries=3
        )

    async def _create_index_with_mapping(self):
        """Define explicit schema for better search accuracy."""
        exists = await self.client.indices.exists(index=self.index_name)
        if not exists:
            logger.info(f"🏗️ Creating optimized index: {self.index_name}")
            body = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0, # Set to 0 for faster initial sync
                    "refresh_interval": "-1" # Disable refresh during bulk load
                },
                "mappings": {
                    "properties": {
                        "name": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "category": {"type": "keyword"},
                        "tags": {"type": "text"},
                        "price": {"type": "float"}
                    }
                }
            }
            await self.client.indices.create(index=self.index_name, body=body)

    async def _product_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Yields documents lazily."""
        async with SessionLocal() as db:
            # 1. Get Total Count
            total_count = (await db.exec(select(func.count(Product.id)))).one()
            logger.info(f"📦 Found {total_count:,} products in SQL Core. Starting Stream...")

            # 2. Stream in Batches
            offset = 0
            while offset < total_count:
                statement = select(Product).offset(offset).limit(self.batch_size)
                result = await db.exec(statement)
                products = result.all()
                
                if not products:
                    break

                for p in products:
                    yield {
                        "_index": self.index_name,
                        "_id": p.id,
                        "_source": {
                            "name": p.name,
                            "description": p.description,
                            "category": p.category,
                            "tags": p.tags,
                            "price": p.price,
                            "rating": p.rating,
                            "image_url": p.image_url
                        }
                    }
                
                offset += len(products)
                logger.info(f"🔄 Processed batch: {offset:,} / {total_count:,}")

    async def sync(self):
        start_time = time.time()
        try:
            await self._create_index_with_mapping()
            
            # 1. Disable Refresh
            await self.client.indices.put_settings(
                index=self.index_name, body={"index": {"refresh_interval": "-1"}}
            )

            # 2. Execute Bulk Upload
            logger.info("🚀 Starting Turbo Sync...")
            success, failed = await helpers.async_bulk(
                self.client,
                self._product_generator(),
                chunk_size=self.batch_size,
                raise_on_error=False,
                request_timeout=120
            )

            # 3. Re-enable Refresh and Optimize
            await self.client.indices.put_settings(
                index=self.index_name, body={"index": {"refresh_interval": "1s"}}
            )
            await self.client.indices.refresh(index=self.index_name) 

            duration = time.time() - start_time
            # --- FIXED LINE BELOW (Added len()) ---
            logger.info(f"✅ Sync Complete in {duration:.2f}s!")
            logger.info(f"📊 Stats: {success:,} indexed | {len(failed):,} failed.") 

        except Exception as e:
            logger.error(f"🔥 Critical Sync Failure: {e}", exc_info=True)
        finally:
            await self.client.close()

if __name__ == "__main__":
    synchronizer = SearchSynchronizer()
    asyncio.run(synchronizer.sync())
