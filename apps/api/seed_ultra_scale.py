import asyncio
import logging
import random
import time
import os
import ujson
from typing import List, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from opensearchpy import AsyncOpenSearch, helpers

# --- 🚀 Milvus & AI Imports ---
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("airdeliver.seeder")

# Constants
BATCH_SIZE = 200  # Reduced for Memory Safety
TARGET_COUNT = int(os.getenv("SEED_TARGET_COUNT", "100000"))
MAX_PRODUCTS_TO_SYNC = 20000 # 🛑 Safety Limit: Stop after 20k items

# --- 🏭 Phase 1: Data Manufacturing (SQL) ---
class ProductFactory:
    """
    Simulates a high-speed production line for product data.
    """
    BASE_PRODUCTS = [
        {"name": "Iphone 17 Pro Max", "cat": "electronics", "price": 1299.99, "tags": ["phone", "premium", "gift"]},
        {"name": "Samsung S25 Ultra", "cat": "electronics", "price": 1199.99, "tags": ["android", "phone", "zoom"]},
        {"name": "Sony WH-1000XM6", "cat": "audio", "price": 399.99, "tags": ["headphone", "noise-canceling", "travel"]},
        {"name": "MacBook Pro M4", "cat": "laptop", "price": 2499.99, "tags": ["laptop", "apple", "work"]},
        {"name": "Nike Air Zoom", "cat": "shoes", "price": 129.99, "tags": ["running", "sport", "shoes"]},
        {"name": "Adidas Ultraboost", "cat": "shoes", "price": 180.00, "tags": ["running", "comfortable", "shoes"]},
        {"name": "Leather Jacket", "cat": "clothing", "price": 250.00, "tags": ["fashion", "leather", "winter"]},
        {"name": "Smart Coffee Maker", "cat": "home", "price": 150.00, "tags": ["coffee", "smart", "kitchen"]},
        {"name": "Gaming Chair", "cat": "furniture", "price": 299.99, "tags": ["gaming", "chair", "comfort"]},
        {"name": "4K OLED Monitor", "cat": "electronics", "price": 899.99, "tags": ["monitor", "screen", "gaming"]}
    ]

    @staticmethod
    def generate_batch(start_id: int, size: int) -> List[Dict]:
        batch = []
        for i in range(size):
            base = random.choice(ProductFactory.BASE_PRODUCTS)
            pid = start_id + i
            item = {
                "id": pid,
                "name": f"{base['name']} - Edition {pid}", # Unique Name
                "description": f"This is the amazing {base['name']}, specifically edition {pid}. Top quality.",
                "price": round(base['price'] * random.uniform(0.9, 1.1), 2),
                "inventory": random.randint(10, 500),
                "image_url": f"/images/product_{random.randint(1, 10)}.jpg", # Mock Image
                "category": base['cat'],
                "tags": ujson.dumps(base['tags']), # SQL needs JSON string
                "rating": round(random.uniform(3.5, 5.0), 1),
                "raw_tags": base['tags'] # For Search Engines
            }
            batch.append(item)
        return batch

async def seed_sql():
    logger.info("🚀 PHASE 1: SQL Data Injection Started...")
    engine = create_async_engine(
        str(settings.DATABASE_URI), # ✅ Fixed Config Name
        echo=False,
        pool_size=10,
        max_overflow=0
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check current count
        result = await session.execute(text("SELECT COUNT(*) FROM products"))
        current_count = result.scalar()
        logger.info(f"📊 Current SQL Count: {current_count}")

        if current_count >= TARGET_COUNT:
            logger.info("✅ SQL Seeding Skipped (Target Reached).")
            return

        needed = TARGET_COUNT - current_count
        start_id = current_count + 1
        
        # Batch Insert
        for i in range(0, needed, 1000):
            current_batch_size = min(1000, needed - i)
            batch = ProductFactory.generate_batch(start_id + i, current_batch_size)
            
            await session.execute(
                text("""
                INSERT INTO products (id, name, description, price, inventory, image_url, category, tags, rating)
                VALUES (:id, :name, :description, :price, :inventory, :image_url, :category, :tags, :rating)
                ON CONFLICT (id) DO NOTHING
                """),
                batch
            )
            await session.commit()
            logger.info(f"📥 Inserted SQL Batch: {current_batch_size} items")

    await engine.dispose()
    logger.info("✅ PHASE 1 COMPLETE.")

# --- 💎 Phase 2: Diamond Sync (OpenSearch + Milvus) ---
async def seed_search_engines():
    logger.info("🚀 PHASE 2: Search Engine Synchronization (Memory Optimized)...")
    
    # 1. Connect to OpenSearch
    os_client = AsyncOpenSearch(
        hosts=[{'host': settings.OPENSEARCH_HOST, 'port': settings.OPENSEARCH_PORT}],
        http_compress=True,
        timeout=60
    )
    
    # 2. Connect to Milvus
    milvus_client = MilvusClient(uri=settings.MILVUS_URI)
    
    # 3. Load AI Models
    logger.info("🧠 Loading AI Models (Takes ~10s)...")
    text_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    vision_model = SentenceTransformer('clip-ViT-B-32')
    logger.info("✅ AI Models Loaded.")

    # 4. Connect to SQL to fetch data
    engine = create_async_engine(str(settings.DATABASE_URI)) # ✅ Fixed Config Name
    async_session = sessionmaker(engine, class_=AsyncSession)

    async with async_session() as session:
        # ✅ Using stream + yield_per for memory safety
        stmt = text("SELECT id, name, description, category, tags, image_url, price, rating FROM products").execution_options(yield_per=BATCH_SIZE)
        result = await session.stream(stmt)
        
        os_batch = []
        milvus_text_batch = []
        milvus_vis_batch = []
        
        count = 0
        
        async for row in result:
            count += 1
            
            # 🛑 STOPPING CONDITION
            if count > MAX_PRODUCTS_TO_SYNC:
                logger.info(f"🛑 Reached Limit: {MAX_PRODUCTS_TO_SYNC} items synced. Stopping safely.")
                break

            item = dict(row._mapping)
            
            # Prepare OpenSearch Doc
            os_doc = {
                "_index": "airdeliver_products",
                "_id": item['id'],
                "_source": {
                    "id": item['id'],
                    "name": item['name'],
                    "description": item['description'],
                    "category": item['category'],
                    "tags": ujson.loads(item['tags']) if isinstance(item['tags'], str) else item['tags'],
                    "price": item['price'],
                    "rating": item['rating'],
                    "image_url": item['image_url']
                }
            }
            os_batch.append(os_doc)

            # Prepare Milvus Vectors
            text_content = f"{item['name']} {item['description']} {item['category']}"
            text_vec = text_model.encode(text_content).tolist()
            milvus_text_batch.append({"id": item['id'], "vector": text_vec})

            vis_content = f"photo of {item['name']}" 
            vis_vec = vision_model.encode(vis_content).tolist()
            milvus_vis_batch.append({"id": item['id'], "image_vector": vis_vec})

            # Flush Batches
            if len(os_batch) >= BATCH_SIZE:
                try:
                    await helpers.async_bulk(os_client, os_batch)
                    milvus_client.insert(collection_name="airdeliver_products", data=milvus_text_batch)
                    milvus_client.insert(collection_name="airdeliver_products_visual", data=milvus_vis_batch)
                    
                    logger.info(f"💎 Synced Batch: {count} items")
                    
                    os_batch = []
                    milvus_text_batch = []
                    milvus_vis_batch = []
                except Exception as e:
                    logger.error(f"❌ Batch Error: {e}")

        # Flush Remaining (if any, and if loop finished naturally)
        if os_batch:
            await helpers.async_bulk(os_client, os_batch)
            milvus_client.insert(collection_name="airdeliver_products", data=milvus_text_batch)
            milvus_client.insert(collection_name="airdeliver_products_visual", data=milvus_vis_batch)
            logger.info(f"💎 Synced Final Batch. Total: {count}")

    await os_client.close()
    await engine.dispose()
    logger.info("✅ PHASE 2 COMPLETE.")

async def main():
    start_time = time.time()
    await seed_sql()
    await seed_search_engines()
    logger.info(f"🏁 MISSION COMPLETE in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())

