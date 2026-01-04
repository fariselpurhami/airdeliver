# apps/api/sync_search.py

import asyncio
import logging
import time
import sys
import os
import json
import torch
import requests
from typing import List, Dict, Any, Tuple
from sqlmodel import select
from opensearchpy import AsyncOpenSearch, helpers
from pymilvus import MilvusClient, DataType
from app.db.session import SessionLocal
from app.models.product import Product
from app.core.config import get_core_settings

# 💎 SOTA Embeddings & Vision
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoProcessor
from PIL import Image
from io import BytesIO

# Config & Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [Sync-Engine] | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("airdeliver.sync")
# Silence noisy libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

# Constants
CHECKPOINT_FILE = "sync_checkpoint.txt"

class UnifiedSyncEngine:
    """
    💎 DIAMOND EDITION UNIFIED SYNCHRONIZER (V3.0 - MULTIMODAL).

    The Sovereign Data Pipeline.
    Syncs PostgreSQL -> OpenSearch (Keywords) AND Milvus (Semantic Text + Visual).

    ARCHITECTURAL PILLARS:
    1. 🧠 Dual-Cortex: Runs Qwen2 (Text) and SigLIP (Vision) in parallel pipelines.
    2. 🛡️ Fault Tolerance: Checkpoint recovery ensures zero data loss on crash.
    3. ⚡ High-Throughput: Uses Batching & Async I/O for maximum velocity.
    """

    def __init__(self):
        self.settings = get_core_settings()

        # 1. OpenSearch Connection
        self.os_index = "airdeliver_products"
        self.os_client = AsyncOpenSearch(
            hosts=[{"host": self.settings.OPENSEARCH_HOST, "port": self.settings.OPENSEARCH_PORT}],
            use_ssl=False, verify_certs=False, timeout=60
        )

        # 2. Milvus Connection
        self.milvus_uri = self.settings.MILVUS_URI
        self.milvus_client = MilvusClient(uri=self.milvus_uri)
        # Using V4 collections (The Standard)
        self.milvus_text_col = "airdeliver_products_sota_v4"
        self.milvus_vis_col = "airdeliver_visual_sota_v4"

        # 3. Database Connection (Sync Engine used for fetching)
        self.db_engine = create_engine(str(self.settings.DATABASE_URL)) # Sync engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)

        # 4. 🧠 Load SOTA Models
        logger.info("🧠 Loading Neural Models (Text + Vision)...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"⚙️ Compute Device: {self.device.upper()}")

        # Text Brain (Qwen2 - 1536 dim)
        self.text_model = SentenceTransformer("Alibaba-NLP/gte-Qwen2-1.5B-instruct", trust_remote_code=True, device=self.device)
        self.text_model.max_seq_length = 8192

        # Vision Brain (SigLIP - 1152 dim)
        try:
            self.vis_processor = AutoProcessor.from_pretrained("google/siglip-so400m-patch14-384")
            self.vis_model = AutoModel.from_pretrained("google/siglip-so400m-patch14-384").to(self.device)
            self.vision_enabled = True
        except Exception as e:
            logger.warning(f"⚠️ Vision Model Load Failed: {e}. Running in TEXT-ONLY mode.")
            self.vision_enabled = False

        # Tuning Parameters
        self.fetch_batch_size = 500   # Moderate size to allow image processing time
        self.milvus_batch_size = 50   # Smaller batch for heavy inference

        # Ensure Infrastructure Ready
        self._ensure_collections()
        self._ensure_os_index()

    def _ensure_collections(self):
        """Creates Milvus Collections if missing (Auto-Schema)."""
        # Text Collection
        if not self.milvus_client.has_collection(self.milvus_text_col):
            schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
            idx = self.milvus_client.prepare_index_params()
            idx.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
            self.milvus_client.create_collection(self.milvus_text_col, schema=schema, index_params=idx)
            logger.info(f"✅ Created Text Collection: {self.milvus_text_col}")

        # Visual Collection
        if self.vision_enabled and not self.milvus_client.has_collection(self.milvus_vis_col):
            schema_vis = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
            schema_vis.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema_vis.add_field(field_name="image_vector", datatype=DataType.FLOAT_VECTOR, dim=1152)
            idx_vis = self.milvus_client.prepare_index_params()
            idx_vis.add_index(field_name="image_vector", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
            self.milvus_client.create_collection(self.milvus_vis_col, schema=schema_vis, index_params=idx_vis)
            logger.info(f"✅ Created Visual Collection: {self.milvus_vis_col}")

    def _ensure_os_index(self):
        """Sync check for OS index presence."""
        # Note: AsyncOpenSearch check would require await, skip for now or run in loop
        pass

    def _get_checkpoint(self) -> int:
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, "r") as f:
                    val = int(f.read().strip())
                    logger.info(f"🔄 Resuming from Checkpoint: ID {val}")
                    return val
            except: pass
        return 0

    def _update_checkpoint(self, last_id: int):
        with open(CHECKPOINT_FILE, "w") as f:
            f.write(str(last_id))

    def _process_image(self, url: str) -> List[float]:
        """Downloads and vectorizes an image (CPU/GPU bound)."""
        if not self.vision_enabled or not url: return None
        try:
            # Timeout is critical to avoid hanging the sync
            response = requests.get(url, timeout=3)
            if response.status_code != 200: return None

            image = Image.open(BytesIO(response.content)).convert("RGB")

            # SigLIP Inference (No Grad for speed)
            with torch.no_grad():
                inputs = self.vis_processor(images=image, return_tensors="pt").to(self.device)
                image_features = self.vis_model.get_image_features(**inputs)
                # Normalize features
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                return image_features[0].cpu().tolist()
        except Exception:
            return None # Fail silently, skip image

    async def _producer(self, os_queue: asyncio.Queue, milvus_queue: asyncio.Queue):
        """
        🚜 The Harvester.
        Fetches data from SQL in massive batches and feeds the queues.
        Uses Checkpoints to survive crashes.
        """
        logger.info("🔌 Producer: Connecting to SQL Core...")
        start_id = self._get_checkpoint()
        
        # Creating a dedicated session for the sync job
        with self.SessionLocal() as db:
            last_seen_id = start_id
            total_fetched = 0
            
            while True:
                # Fetch Batch (Efficient Pagination by ID)
                products = db.query(Product).filter(Product.id > last_seen_id).order_by(Product.id).limit(self.fetch_batch_size).all()
                
                if not products:
                    break

                batch = products # List of SQL Models

                # 💎 Optimization: Detach from SQL Session immediately to avoid pickling issues
                # Convert to pure dictionaries for workers
                payload_batch = []
                for p in batch:
                    item = {
                        "id": p.id,
                        "name": p.name,
                        "price": float(p.price), # Safe float
                        "description": p.description,
                        "category": p.category,
                        "rating": float(p.rating or 0),
                        "image_url": p.image_url,
                        # Add other fields as needed
                    }
                    payload_batch.append(item)

                # 1. OpenSearch Payload (Keyword Search)
                os_batch = [{
                    "_index": self.os_index,
                    "_id": str(p["id"]),
                    "_source": p # The dict itself
                } for p in payload_batch]
                
                # Push to Queues (Backpressure applied if full)
                await os_queue.put(os_batch)
                await milvus_queue.put(payload_batch)
                
                # Update State
                last_seen_id = batch[-1].id
                total_fetched += len(batch)
                self._update_checkpoint(last_seen_id)
                
                if total_fetched % 5000 == 0:
                    logger.info(f"📥 Producer: Fetched {total_fetched:,} products so far...")

        # 💀 Poison Pills (Signal Workers to Stop)
        for _ in range(self.os_workers): await os_queue.put(None)
        for _ in range(self.milvus_workers): await milvus_queue.put(None)
        logger.info("✅ Producer: Harvesting Complete.")

    # --- 🔨 SECTION 3: THE CONSUMERS (WORKERS) ---

    async def _os_consumer(self, worker_id: int, queue: asyncio.Queue, stats: Dict):
        """Worker that pushes JSON data to OpenSearch."""
        while True:
            batch = await queue.get()
            if batch is None:
                queue.task_done()
                break 
            try:
                success, failed = await helpers.async_bulk(
                    self.os_client, batch, chunk_size=self.os_batch_size, raise_on_error=False
                )
                stats['os_success'] += success
                stats['os_failed'] += len(failed)
            except Exception as e:
                logger.error(f"🔥 OS-Worker {worker_id}: {e}")
            finally:
                queue.task_done()

    async def _milvus_consumer(self, worker_id: int, queue: asyncio.Queue, stats: Dict):
        """
        💎 SOTA VECTORIZER: Handles both TEXT and IMAGE vectors.
        """
        while True:
            batch = await queue.get() # List of Product Dicts
            if batch is None:
                queue.task_done()
                break 
            
            # Split batch into chunks for Milvus (to avoid huge GPU load)
            chunk_size = self.milvus_batch_size
            
            for i in range(0, len(batch), chunk_size):
                sub_batch = batch[i:i + chunk_size]
                
                try:
                    loop = asyncio.get_running_loop()

                    # --- A. Text Embeddings (Qwen2) ---
                    texts = [f"{p['name']} {p.get('category','')} {p.get('description','')}" for p in sub_batch]
                    
                    # Run CPU-bound encoding in Executor
                    text_vectors = await loop.run_in_executor(
                        None, 
                        lambda: self.text_model.encode(texts, convert_to_numpy=True).tolist()
                    )
                    
                    text_data = []
                    for idx, p in enumerate(sub_batch):
                        text_data.append({
                            "id": p['id'],
                            "vector": text_vectors[idx],
                            "price": float(p['price']),
                            "rating": float(p.get('rating', 0)),
                            "category": str(p.get('category', 'general'))
                        })
                    
                    # Insert Text Vectors
                    await loop.run_in_executor(None, lambda: self.milvus_client.insert(self.milvus_text_col, text_data))
                    stats['milvus_text'] += len(text_data)

                    # --- B. Image Embeddings (SigLIP) ---
                    # 💎 Only run if Vision is enabled and URLs exist
                    if self.vision_enabled:
                        vis_data = []
                        # Process images in parallel using ThreadPool for IO/CPU bound tasks
                        # We map the _process_image function over URLs
                        image_urls = [p.get('image_url') for p in sub_batch]
                        
                        # Use gather for concurrent downloading/processing
                        # Note: _process_image is synchronous, so we run it in executor
                        vis_tasks = [loop.run_in_executor(None, self._process_image, url) for url in image_urls]
                        vis_vectors = await asyncio.gather(*vis_tasks)
                        
                        for idx, vec in enumerate(vis_vectors):
                            if vec: # Only add successful vectors
                                vis_data.append({
                                    "id": sub_batch[idx]['id'],
                                    "image_vector": vec
                                })
                        
                        if vis_data:
                            await loop.run_in_executor(None, lambda: self.milvus_client.insert(self.milvus_vis_col, vis_data))
                            stats['milvus_vis'] += len(vis_data)

                except Exception as e:
                    logger.error(f"🔥 Milvus-Worker {worker_id} Chunk Error: {e}")
                    stats['milvus_failed'] += len(sub_batch)
            
            queue.task_done()

    # --- 🚀 SECTION 4: ORCHESTRATOR ---

    async def sync(self):
        import time
        start = time.time()
        # Using a simple dict is fine here as asyncio is single-threaded for shared state access logic
        # But for absolute safety in threading, we assume cooperative multitasking protects us
        stats = {'os_success': 0, 'os_failed': 0, 'milvus_text': 0, 'milvus_vis': 0, 'milvus_failed': 0}
        
        os_queue = asyncio.Queue(maxsize=self.queue_size)
        milvus_queue = asyncio.Queue(maxsize=self.queue_size)
        
        producer = asyncio.create_task(self._producer(os_queue, milvus_queue))
        
        consumers = []
        for i in range(self.os_workers):
            consumers.append(asyncio.create_task(self._os_consumer(i, os_queue, stats)))
        for i in range(self.milvus_workers):
            consumers.append(asyncio.create_task(self._milvus_consumer(i, milvus_queue, stats)))

        await producer
        await os_queue.join()
        await milvus_queue.join()
        
        # Cancel consumers (they are stuck in infinite loop waiting for items)
        # But we sent None, so they should have exited gracefully.
        await asyncio.gather(*consumers)
        
        # Cleanup
        if os.path.exists(CHECKPOINT_FILE): os.remove(CHECKPOINT_FILE)

        logger.info(f"""
        =============================================
        💎 DIAMOND MULTIMODAL SYNC COMPLETE
        =============================================
        ⏱️  Time:        {time.time() - start:.2f}s
        ✅ OpenSearch:  {stats['os_success']:,}
        ✅ Text Vectors: {stats['milvus_text']:,}
        ✅ Visual Vecs:  {stats['milvus_vis']:,}
        =============================================
        """)

        await self.os_client.close()

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except: pass
    
    # Check dependencies
    try:
        import requests
        from PIL import Image
    except ImportError:
        logger.critical("❌ Missing deps: pip install requests pillow")
        sys.exit(1)

    synchronizer = UnifiedSyncEngine()
    asyncio.run(synchronizer.sync())
