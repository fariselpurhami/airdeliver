import asyncio
import logging
import os
import random
import json
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, func, select
from sentence_transformers import SentenceTransformer
from opensearchpy import AsyncOpenSearch, helpers
from pymilvus import MilvusClient, DataType

# -----------------------------------------------------------------------------
# 1. Global Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("airdeliver.seeder_global")

DB_URL = os.getenv("DATABASE_URI", "postgresql+asyncpg://postgres:postgres@postgres:5432/airdeliver")
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "opensearch")
MILVUS_URI = "http://milvus:19530"
MODEL_TEXT_SOTA = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
TEXT_COL = "airdeliver_products_sota_v4"
BATCH_SIZE = 64
TARGET_COUNT = 1000

# -----------------------------------------------------------------------------
# 2. Smart Product Templates (Context-Aware)
# -----------------------------------------------------------------------------
CATALOG_DATA = {
    "Smartphones": {
        "products": [
            {"name": "Apple iPhone 15 Pro Max", "base_price": 1199, "img": "https://images.unsplash.com/photo-1696446701796-da61225697cc?auto=format&fit=crop&w=800&q=80"},
            {"name": "Samsung Galaxy S24 Ultra", "base_price": 1299, "img": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=800&q=80"},
            {"name": "Google Pixel 8 Pro", "base_price": 999, "img": "https://images.unsplash.com/photo-1698669930852-25916053f317?auto=format&fit=crop&w=800&q=80"},
            {"name": "Sony Xperia 1 V", "base_price": 1399, "img": "https://images.unsplash.com/photo-1596742517684-29729a656515?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["256GB", "512GB", "1TB", "Titanium Frame", "AI Camera"],
        "colors": ["Natural Titanium", "Blue Titanium", "Black Titanium", "White Titanium", "Phantom Black", "Cream"]
    },
    "Laptops": {
        "products": [
            {"name": "MacBook Pro 16 M3 Max", "base_price": 2499, "img": "https://images.unsplash.com/photo-1517336714731-489689fd1ca4?auto=format&fit=crop&w=800&q=80"},
            {"name": "Dell XPS 15 OLED", "base_price": 1899, "img": "https://images.unsplash.com/photo-1593642632823-8f78536788c6?auto=format&fit=crop&w=800&q=80"},
            {"name": "Razer Blade 18 Gaming", "base_price": 3299, "img": "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=800&q=80"},
            {"name": "Asus ROG Zephyrus G14", "base_price": 1599, "img": "https://images.unsplash.com/photo-1628122393356-97987820d880?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["16GB RAM", "32GB RAM", "64GB RAM", "1TB SSD", "2TB SSD", "RTX 4090"],
        "colors": ["Space Grey", "Silver", "Midnight", "Mercury White", "Matte Black"]
    },
    "Headphones": {
        "products": [
            {"name": "Sony WH-1000XM5", "base_price": 348, "img": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=800&q=80"},
            {"name": "Apple AirPods Max", "base_price": 549, "img": "https://images.unsplash.com/photo-1613040809024-b4ef7ba99bc3?auto=format&fit=crop&w=800&q=80"},
            {"name": "Bose QuietComfort Ultra", "base_price": 429, "img": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["Noise Cancelling", "Lossless Audio", "Spatial Audio", "30-Hour Battery"],
        "colors": ["Silver", "Space Grey", "Sky Blue", "Pink", "Green", "Black"]
    },
    "Cameras": {
        "products": [
            {"name": "Sony Alpha a7 IV", "base_price": 2498, "img": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=800&q=80"},
            {"name": "Canon EOS R5", "base_price": 3899, "img": "https://images.unsplash.com/photo-1519183071298-a2962feb14f4?auto=format&fit=crop&w=800&q=80"},
            {"name": "Fujifilm X-T5", "base_price": 1699, "img": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["Body Only", "with 24-70mm Lens", "with 50mm Lens", "8K Video"],
        "colors": ["Black", "Silver", "Retro Styling"]
    },
    "Drones": {
        "products": [
            {"name": "DJI Mavic 3 Pro", "base_price": 2199, "img": "https://images.unsplash.com/photo-1579829366248-204fe8413f31?auto=format&fit=crop&w=800&q=80"},
            {"name": "DJI Mini 4 Pro", "base_price": 759, "img": "https://images.unsplash.com/photo-1473968512647-3e447244af8f?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["Fly More Combo", "RC Controller", "Cine Premium Combo"],
        "colors": ["Classic Grey", "Light Grey"]
    },
    "Watches": {
        "products": [
            {"name": "Apple Watch Ultra 2", "base_price": 799, "img": "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=800&q=80"},
            {"name": "Garmin Fenix 7X Pro", "base_price": 899, "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"},
            {"name": "Samsung Galaxy Watch 6", "base_price": 299, "img": "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80"},
        ],
        "specs": ["49mm", "45mm", "GPS + Cellular", "GPS Only", "Sapphire Solar"],
        "colors": ["Titanium", "Midnight", "Starlight", "Graphite"]
    }
}

# -----------------------------------------------------------------------------
# 3. Seeding Logic with Resume Capability
# -----------------------------------------------------------------------------
async def seed_search_engines():
    logger.info("🚀 STARTING GLOBAL ARCHITECTURE SEEDING SEQUENCE (RESUMABLE MODE)...")
    
    os_client = None
    engine = None

    try:
        # --- Connect Services ---
        milvus = MilvusClient(uri=MILVUS_URI)
        os_client = AsyncOpenSearch(hosts=[{'host': OPENSEARCH_HOST, 'port': 9200}], timeout=60)
        
        logger.info("🧠 Loading Neural Model...")
        # 💎 FIXED: Set trust_remote_code=False to avoid rope_theta conflict
        model = SentenceTransformer(MODEL_TEXT_SOTA, device="cpu", trust_remote_code=False)
        embedding_dim = model.get_sentence_embedding_dimension()

        # --- Setup Postgres Connection ---
        engine = create_async_engine(DB_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        start_index = 1
        
        # --- 🔄 RESUME CHECK LOGIC ---
        async with async_session() as session:
            logger.info("🛡️ Checking existing data for resume capability...")
            await session.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image VARCHAR(1024);"))
            await session.commit()
            
            # Check maximum ID currently in DB
            result = await session.execute(text("SELECT MAX(id) FROM products"))
            max_id = result.scalar()
            
            if max_id:
                logger.info(f"⚠️ Found existing data! Resuming from ID: {max_id + 1}")
                start_index = max_id + 1
            else:
                logger.info("✅ No existing data found. Starting fresh from ID: 1")
                # Setup Milvus only on fresh start to keep schema in sync
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
                
                # Setup OpenSearch only on fresh start
                await os_client.indices.delete(index="airdeliver_products", ignore=[400, 404])

        if start_index > TARGET_COUNT:
            logger.info("🎉 Target count already reached! No new data needed.")
            return

        # --- Generation & Batch Processing Loop ---
        current_id = start_index
        categories_keys = list(CATALOG_DATA.keys())
        now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)

        # Loop until we reach target
        while current_id <= TARGET_COUNT:
            batch_products_pg = []
            batch_products_meta = []
            
            # Generate a batch
            batch_end = min(current_id + BATCH_SIZE, TARGET_COUNT + 1)
            
            logger.info(f"⚡ Processing batch: IDs {current_id} to {batch_end - 1}...")

            for i in range(current_id, batch_end):
                cat_key = random.choice(categories_keys)
                cat_data = CATALOG_DATA[cat_key]
                template = random.choice(cat_data["products"])
                variant_spec = random.choice(cat_data["specs"])
                variant_color = random.choice(cat_data["colors"])
                
                full_name = f"{template['name']} - {variant_spec} ({variant_color})"
                
                base_price = template['base_price']
                price_modifier = 1.0
                if "1TB" in variant_spec or "Pro" in variant_spec or "Max" in variant_spec:
                    price_modifier = 1.2
                
                final_price = round(base_price * price_modifier * random.uniform(0.95, 1.05), 2)

                desc = (
                    f"Experience the pinnacle of {cat_key} technology with the {full_name}. "
                    f"Designed in a stunning {variant_color} finish and equipped with {variant_spec}. "
                    f"Perfect for those who demand excellence in performance and style. "
                    f"Official AirDeliver Global Stock."
                )

                image_url = template['img']
                tags_py = [cat_key, "Premium", variant_color, template['name'].split()[0], "Official"]
                
                # 🔥 FIX: Generate SKU here
                generated_sku = f"GLB-{cat_key[:3].upper()}-{i:04d}"

                # Postgres Object
                pg_obj = {
                    "id": i,
                    "sku": generated_sku, # 👈 Added SKU here
                    "name": full_name,
                    "description": desc,
                    "price": Decimal(str(final_price)),
                    "category": cat_key,
                    "inventory": random.randint(5, 500),
                    "image": image_url,
                    "rating": round(random.uniform(3.5, 5.0), 1),
                    "tags": json.dumps(tags_py),
                    "created_at": now_utc_naive,
                    "updated_at": now_utc_naive,
                    "currency": "USD",
                    "is_active": True
                }
                batch_products_pg.append(pg_obj)

                # Meta Object for Vector DBs
                meta_obj = pg_obj.copy()
                meta_obj["tags"] = tags_py # Keep as list for embedding
                meta_obj["price"] = final_price # Float for embedding
                batch_products_meta.append(meta_obj)

            # --- Embedding & Saving Batch ---
            if not batch_products_pg:
                break

            # 1. Embed Batch
            texts = [f"{item['name']} {item['description']} {' '.join(item['tags'])}" for item in batch_products_meta]
            embeddings = model.encode(texts, normalize_embeddings=True)

            # 2. Save to Postgres
            async with async_session() as session:
                await session.execute(
                    text("""
                    INSERT INTO products (id, sku, name, description, price, category, inventory, image, rating, tags, created_at, updated_at, currency, is_active)
                    VALUES (:id, :sku, :name, :description, :price, :category, :inventory, :image, :rating, :tags, :created_at, :updated_at, :currency, :is_active)
                    ON CONFLICT (id) DO NOTHING
                    """),
                    batch_products_pg
                )
                await session.commit()

            # 3. Save to Milvus
            milvus_data = []
            for idx, item in enumerate(batch_products_meta):
                milvus_data.append({
                    "id": item["id"],
                    "vector": embeddings[idx].tolist(),
                    "price": item["price"],
                    "rating": item["rating"],
                    "category": item["category"]
                })
            milvus.insert(collection_name=TEXT_COL, data=milvus_data)

            # 4. Save to OpenSearch
            os_actions = []
            for idx, item in enumerate(batch_products_meta):
                doc = item.copy()
                doc["vector"] = embeddings[idx].tolist()
                # Remove non-serializable objects for JSON
                del doc["created_at"]
                del doc["updated_at"]
                os_actions.append({
                    "_index": "airdeliver_products",
                    "_id": item["id"],
                    "_source": doc
                })
            await helpers.async_bulk(os_client, os_actions)

            logger.info(f"   ✅ Saved batch ending at ID {batch_end - 1}")
            current_id = batch_end # Update loop counter

        logger.info(f"🎉 GLOBAL SEEDING COMPLETE. Reached target ID: {TARGET_COUNT}.")

    except Exception as e:
        logger.error(f"❌ SEEDING FAILED: {str(e)}")
        raise
    finally:
        if engine:
            await engine.dispose()
        if os_client:
            await os_client.close()

if __name__ == "__main__":
    asyncio.run(seed_search_engines())
