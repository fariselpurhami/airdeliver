import asyncio
import logging
import os
import random
import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from opensearchpy import AsyncOpenSearch, helpers
from pymilvus import MilvusClient, DataType

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("airdeliver.seeder_global")

DB_URL = os.getenv("DATABASE_URI", "postgresql+asyncpg://postgres:postgres@postgres:5432/airdeliver")
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
MILVUS_URI = "http://milvus:19530"
MODEL_TEXT_SOTA = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
TEXT_COL = "airdeliver_products_sota_v4"
BATCH_SIZE = 64

PRODUCT_TEMPLATES = {
    "Smartphones": [
        {"name": "Apple iPhone 15 Pro Max", "base_price": 1199, "img": "https://images.unsplash.com/photo-1696446701796-da61225697cc?auto=format&fit=crop&w=800&q=80"},
        {"name": "Samsung Galaxy S24 Ultra", "base_price": 1299, "img": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=800&q=80"},
        {"name": "Google Pixel 8 Pro", "base_price": 999, "img": "https://images.unsplash.com/photo-1698669930852-25916053f317?auto=format&fit=crop&w=800&q=80"},
        {"name": "Sony Xperia 1 V", "base_price": 1399, "img": "https://images.unsplash.com/photo-1596742517684-29729a656515?auto=format&fit=crop&w=800&q=80"},
    ],
    "Laptops": [
        {"name": "MacBook Pro 16 M3 Max", "base_price": 2499, "img": "https://images.unsplash.com/photo-1517336714731-489689fd1ca4?auto=format&fit=crop&w=800&q=80"},
        {"name": "Dell XPS 15 OLED", "base_price": 1899, "img": "https://images.unsplash.com/photo-1593642632823-8f78536788c6?auto=format&fit=crop&w=800&q=80"},
        {"name": "Razer Blade 18 Gaming", "base_price": 3299, "img": "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=800&q=80"},
        {"name": "Asus ROG Zephyrus G14", "base_price": 1599, "img": "https://images.unsplash.com/photo-1628122393356-97987820d880?auto=format&fit=crop&w=800&q=80"},
    ],
    "Headphones": [
        {"name": "Sony WH-1000XM5", "base_price": 348, "img": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=800&q=80"},
        {"name": "Apple AirPods Max", "base_price": 549, "img": "https://images.unsplash.com/photo-1613040809024-b4ef7ba99bc3?auto=format&fit=crop&w=800&q=80"},
        {"name": "Bose QuietComfort Ultra", "base_price": 429, "img": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80"},
    ],
    "Cameras": [
        {"name": "Sony Alpha a7 IV", "base_price": 2498, "img": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80"},
        {"name": "Canon EOS R5", "base_price": 3899, "img": "https://images.unsplash.com/photo-1519183071298-a2962feb14f4?auto=format&fit=crop&w=800&q=80"},
        {"name": "Fujifilm X-T5", "base_price": 1699, "img": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=800&q=80"},
    ],
    "Drones": [
        {"name": "DJI Mavic 3 Pro", "base_price": 2199, "img": "https://images.unsplash.com/photo-1579829366248-204fe8413f31?auto=format&fit=crop&w=800&q=80"},
        {"name": "DJI Mini 4 Pro", "base_price": 759, "img": "https://images.unsplash.com/photo-1473968512647-3e447244af8f?auto=format&fit=crop&w=800&q=80"},
    ],
    "Watches": [
        {"name": "Apple Watch Ultra 2", "base_price": 799, "img": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=800&q=80"},
        {"name": "Garmin Fenix 7X Pro", "base_price": 899, "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"},
        {"name": "Samsung Galaxy Watch 6", "base_price": 299, "img": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80"},
    ]
}

VARIANTS = ["Midnight Black", "Titanium Silver", "Ocean Blue", "Space Grey", "Sunset Gold", "Arctic White"]
SPECS_KEYWORDS = ["512GB", "1TB", "256GB", "Pro Performance", "AI Edition", "Limited Series"]

async def seed_search_engines():
    logger.info("�� STARTING GLOBAL ARCHITECTURE SEEDING SEQUENCE...")
    os_client = None
    engine = None
    
    try:
        milvus = MilvusClient(uri=MILVUS_URI)
        os_client = AsyncOpenSearch(hosts=[{'host': OPENSEARCH_HOST, 'port': 9200}], timeout=60)
        
        logger.info("🧠 Loading Neural Model...")
        model = SentenceTransformer(MODEL_TEXT_SOTA, device="cpu", trust_remote_code=False)
        embedding_dim = model.get_sentence_embedding_dimension()

        if milvus.has_collection(TEXT_COL):
            milvus.drop_collection(TEXT_COL)

        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=embedding_dim)
        schema.add_field("price", DataType.DOUBLE)
        schema.add_field("rating", DataType.DOUBLE)
        schema.add_field("category", DataType.VARCHAR, max_length=512)

        index_params = milvus.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="AUTOINDEX")

        milvus.create_collection(
            collection_name=TEXT_COL,
            schema=schema,
            index_params=index_params
        )

        await os_client.indices.delete(index="airdeliver_products", ignore=[400, 404])

        engine = create_async_engine(DB_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            logger.info("🛡️ Performing Self-Healing Schema Check...")
            await session.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image VARCHAR(1024);"))
            await session.commit()
            logger.info("✅ Schema Verified.")

        products_list = []
        pg_products_list = []
        now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        
        categories = list(PRODUCT_TEMPLATES.keys())
        
        for i in range(1, 1001):
            cat = random.choice(categories)
            template = random.choice(PRODUCT_TEMPLATES[cat])
            variant_color = random.choice(VARIANTS)
            variant_spec = random.choice(SPECS_KEYWORDS)
            
            full_name = f"{template['name']} ({variant_spec}, {variant_color})"
            base_price = template['base_price']
            final_price = round(base_price * random.uniform(0.9, 1.2), 2)
            
            desc = (
                f"Experience the ultimate {cat} with the {full_name}. "
                f"Featuring state-of-the-art technology, premium {variant_color} finish, and {variant_spec} configuration. "
                f"Perfect for professionals and enthusiasts seeking top-tier performance."
            )

            image_url = template['img']
            tags_py = [cat, "Premium", variant_color, template['name'].split()[0], "Global Store"]

            p = {
                "id": i,
                "sku": f"GLB-{cat[:3].upper()}-{i:04d}",
                "name": full_name,
                "description": desc,
                "price": final_price,
                "category": cat,
                "inventory": random.randint(5, 500),
                "rating": round(random.uniform(4.2, 5.0), 1),
                "tags": tags_py,
                "image": image_url,
                "is_active": True,
                "created_at": now_utc_naive,
                "updated_at": now_utc_naive
            }
            products_list.append(p)

            pg_p = p.copy()
            pg_p['tags'] = json.dumps(tags_py)
            pg_products_list.append(pg_p)

        logger.info("💉 Injecting Data into PostgreSQL...")
        
        async with async_session() as session:
            stmt = text("""
                INSERT INTO products (id, sku, name, description, price, inventory, category, rating, tags, image, is_active, created_at, updated_at)
                VALUES (:id, :sku, :name, :description, :price, :inventory, :category, :rating, :tags, :image, :is_active, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET 
                    sku = EXCLUDED.sku,
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    price = EXCLUDED.price,
                    rating = EXCLUDED.rating,
                    category = EXCLUDED.category,
                    tags = EXCLUDED.tags,
                    image = EXCLUDED.image,
                    inventory = EXCLUDED.inventory,
                    updated_at = EXCLUDED.updated_at
            """)
            
            await session.execute(stmt, pg_products_list)
            await session.commit()
            logger.info("✅ Database Synchronization Complete.")

        total = len(products_list)
        logger.info(f"📦 Synchronizing {total} vectors to AI Core...")

        for i in range(0, total, BATCH_SIZE):
            chunk_dicts = products_list[i:i+BATCH_SIZE]
            
            texts = [
                f"Product: {d['name']}. Category: {d['category']}. "
                f"Color: {d['tags'][2]}. Specs: {d['description']}" 
                for d in chunk_dicts
            ]
            
            embeddings = model.encode(texts, convert_to_tensor=False).tolist()

            os_batch, mil_batch = [], []
            for idx, d in enumerate(chunk_dicts):
                p_id = str(d['id'])
                emb = embeddings[idx]

                os_batch.append({
                    "_index": "airdeliver_products",
                    "_id": p_id,
                    "_source": {
                        **d,
                        "embedding": emb,
                        "id": p_id,
                        "created_at": d['created_at'].isoformat(),
                        "updated_at": d['updated_at'].isoformat()
                    }
                })

                mil_batch.append({
                    "id": int(p_id),
                    "vector": emb,
                    "price": d['price'],
                    "rating": d['rating'],
                    "category": str(d.get('category', '')),
                    "payload": {"product_id": p_id, "sku": d['sku'], "image": d['image']} 
                })

            await helpers.async_bulk(os_client, os_batch)
            milvus.insert(TEXT_COL, mil_batch)
            
            logger.info(f"⚡ Batch Synced: {min(i+BATCH_SIZE, total)}/{total}")

    except Exception as e:
        logger.error(f"❌ EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if engine:
            await engine.dispose()
        if os_client:
            await os_client.close()

if __name__ == "__main__":
    asyncio.run(seed_search_engines())
