# apps/api/sync_search.py

# apps/api/sync_search.py

import asyncio
import json
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import torch
from opensearchpy import AsyncOpenSearch, helpers
from PIL import Image
from pymilvus import DataType, MilvusClient
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from transformers import AutoModel, AutoProcessor

from app.core.config import get_core_settings
from app.core.catalog_contract import PRODUCT_TEXT_MODEL_NAME,PRODUCT_TEXT_MODEL_DIMENSION,PRODUCT_TEXT_COLLECTION,PRODUCT_SEARCH_INDEX,DEFAULT_PRODUCT_TEXT_MODEL_REVISION
from app.models.product import Product

# --- CONSTANTS & CONFIGURATION ---

CHECKPOINT_FILE = "sync_checkpoint.json" if PRODUCT_TEXT_MODEL_DIMENSION==1536 else "sync_checkpoint_harrier_v1.json"
MAX_SEQ_LENGTH = 8192
MILVUS_TEXT_DIM = PRODUCT_TEXT_MODEL_DIMENSION
MILVUS_VIS_DIM = 1152
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 200

# Structured Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(name)s] | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("airdeliver.sync")

# Silence verbose third-party loggers
for noisy_logger in ["urllib3", "sentence_transformers", "transformers", "opensearch", "httpx"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)


# --- DOMAIN MODELS ---

@dataclass
class ProductPayload:
    """Internal representation of a product strictly typed for pipeline safety."""
    id: int
    name: str
    price: float
    description: str
    category: str
    rating: float
    image_url: Optional[str]

    @property
    def semantic_text(self) -> str:
        """Constructs the dense representation for embedding."""
        return f"{self.name} {self.category} {self.description}".strip()


@dataclass
class SyncMetrics:
    """Thread-safe synchronization telemetry."""
    fetched: int = 0
    os_success: int = 0
    os_failed: int = 0
    milvus_text_success: int = 0
    milvus_vis_success: int = 0
    milvus_failed: int = 0
    start_time: float = field(default_factory=asyncio.get_event_loop().time if asyncio.get_event_loop().is_running() else 0.0)


# --- INFRASTRUCTURE & STATE MANAGEMENT ---

class CheckpointManager:
    """Atomic file-based checkpoint state machine to guarantee at-least-once processing semantics."""

    def __init__(self, filepath: str = CHECKPOINT_FILE):
        self.filepath = filepath

    def get_last_id(self) -> int:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)
                    last_id = data.get("last_processed_id", 0)
                    logger.info(f"🔄 Resuming from Checkpoint: ID {last_id}")
                    return last_id
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Checkpoint corruption detected, starting from 0. Error: {e}")
        return 0

    def commit(self, last_id: int) -> None:
        """Atomic write to prevent corruption during crash."""
        temp_file = f"{self.filepath}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump({"last_processed_id": last_id}, f)
            os.replace(temp_file, self.filepath)
        except IOError as e:
            logger.error(f"Failed to commit checkpoint: {e}")

    def clear(self) -> None:
        if os.path.exists(self.filepath):
            os.remove(self.filepath)


class NeuralInferenceEngine:
    """
    Isolated computational engine for Deep Learning models.
    Operates strictly within a ThreadPoolExecutor to prevent blocking the Async Event Loop.
    """

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"⚙️ Initializing Compute Architecture on: {self.device.type.upper()}")

        if PRODUCT_TEXT_MODEL_DIMENSION!=1536:
            raise ValueError("Legacy sync serialization is not Harrier importer-compatible; use scripts/migrate_harrier_catalog.py")
        # Load Text Model (Qwen2)
        self.text_model = SentenceTransformer(PRODUCT_TEXT_MODEL_NAME, revision=DEFAULT_PRODUCT_TEXT_MODEL_REVISION, trust_remote_code=False, device=self.device)
        self.text_model.max_seq_length = MAX_SEQ_LENGTH

        # Load Vision Model (SigLIP)
        self.vision_enabled = False
        try:
            self.vis_processor = AutoProcessor.from_pretrained("google/siglip-so400m-patch14-384")
            self.vis_model = AutoModel.from_pretrained("google/siglip-so400m-patch14-384").to(self.device)
            self.vis_model.eval()
            self.vision_enabled = True
            logger.info("👁️ Vision Architecture (SigLIP) successfully initialized.")
        except Exception as e:
            logger.warning(f"⚠️ Vision initialization bypassed: {e}. Degrading to TEXT-ONLY mode.")

    def encode_text_batch(self, texts: List[str]) -> List[List[float]]:
        """Encodes a batch of strings into dense vectors. CPU/GPU bound."""
        vectors = self.text_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.tolist()

    def encode_image(self, image_bytes: bytes) -> Optional[List[float]]:
        """Processes raw image bytes into a dense vector using SigLIP. CPU/GPU bound."""
        if not self.vision_enabled:
            return None

        try:
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            with torch.inference_mode():
                inputs = self.vis_processor(images=image, return_tensors="pt").to(self.device)
                features = self.vis_model.get_image_features(**inputs)
                features = features / features.norm(p=2, dim=-1, keepdim=True)
                return features[0].cpu().tolist()
        except Exception as e:
            logger.error(f"Image tensor processing failure: {e}")
            return None


# --- ORCHESTRATOR PIPELINE ---

class UnifiedSyncPipeline:
    """
    DIAMOND EDITION UNIFIED SYNCHRONIZER.

    Enterprise-grade robust data pipeline ensuring absolute consistency across
    relational (PostgreSQL), semantic (Milvus), and keyword (OpenSearch) bounds.
    """

    def __init__(self):
        self.settings = get_core_settings()
        self.metrics = SyncMetrics()
        self.checkpoint = CheckpointManager()
        self.inference_engine = NeuralInferenceEngine()

        # Concurrency & Batching Limits
        self.fetch_batch_size = 1000
        self.os_batch_size = 500
        self.milvus_batch_size = 50
        self.queue_max_size = 5000
        self.os_workers = 2
        self.milvus_workers = 3

        # Graceful Shutdown Event
        self._stop_event = asyncio.Event()
        self._thread_pool = ThreadPoolExecutor(max_workers=self.milvus_workers + 1)

        self._init_infrastructure()

    def _init_infrastructure(self):
        """Initializes client connections and asserts remote schema boundaries."""
        # 1. Database Configuration
        # Must utilize async_engine to avoid blocking the I/O loop
        db_url = str(self.settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")
        self.db_engine = create_async_engine(db_url, pool_size=5, max_overflow=10)
        self.AsyncSessionLocal = sessionmaker(self.db_engine, class_=AsyncSession, expire_on_commit=False)

        # 2. OpenSearch Configuration
        self.os_index = PRODUCT_SEARCH_INDEX
        self.os_client = AsyncOpenSearch(
            hosts=[{"host": self.settings.OPENSEARCH_HOST, "port": self.settings.OPENSEARCH_PORT}],
            use_ssl=False, verify_certs=False, timeout=30
        )

        # 3. Milvus Configuration
        self.milvus_client = MilvusClient(uri=self.settings.MILVUS_URI)
        self.milvus_text_col = PRODUCT_TEXT_COLLECTION
        self.milvus_vis_col = "airdeliver_visual_sota_v4"
        self._assert_milvus_schemas()

    def _assert_milvus_schemas(self) -> None:
        """Idempotent assertion of distributed vector schemas."""
        try:
            if not self.milvus_client.has_collection(self.milvus_text_col):
                schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
                schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
                schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=MILVUS_TEXT_DIM)
                idx = self.milvus_client.prepare_index_params()
                idx.add_index(field_name="vector", index_type="HNSW", metric_type="COSINE", params={"M": HNSW_M, "efConstruction": HNSW_EF_CONSTRUCTION})
                self.milvus_client.create_collection(self.milvus_text_col, schema=schema, index_params=idx)
                logger.info(f"✅ Text vector schema provisioned: {self.milvus_text_col}")

            if self.inference_engine.vision_enabled and not self.milvus_client.has_collection(self.milvus_vis_col):
                schema_vis = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
                schema_vis.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
                schema_vis.add_field(field_name="image_vector", datatype=DataType.FLOAT_VECTOR, dim=MILVUS_VIS_DIM)
                idx_vis = self.milvus_client.prepare_index_params()
                idx_vis.add_index(field_name="image_vector", index_type="HNSW", metric_type="COSINE", params={"M": HNSW_M, "efConstruction": HNSW_EF_CONSTRUCTION})
                self.milvus_client.create_collection(self.milvus_vis_col, schema=schema_vis, index_params=idx_vis)
                logger.info(f"✅ Vision vector schema provisioned: {self.milvus_vis_col}")
        except Exception as e:
            logger.critical(f"Milvus schema assertion failed. Infrastructure unresponsive: {e}")
            sys.exit(1)

    async def _download_image(self, session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
        """Asynchronous HTTP ingestion with strict timeout and payload limits."""
        if not url:
            return None
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return await response.read()
        except aiohttp.ClientError as e:
            logger.debug(f"Image retrieval failed for {url}: {e}")
        except asyncio.TimeoutError:
            logger.debug(f"Image retrieval timeout for {url}")
        return None

    # --- PIPELINE WORKERS ---

    async def _producer(self, os_queue: asyncio.Queue, milvus_queue: asyncio.Queue) -> None:
        """Extracts domains from Postgres and buffers them into routing queues."""
        logger.info("🚜 Upstream Harvester Online.")
        last_seen_id = self.checkpoint.get_last_id()

        try:
            async with self.AsyncSessionLocal() as db:
                while not self._stop_event.is_set():
                    stmt = select(Product).where(Product.id > last_seen_id).order_by(Product.id).limit(self.fetch_batch_size)
                    result = await db.execute(stmt)
                    products = result.scalars().all()

                    if not products:
                        logger.info("🚜 Upstream Harvester Exhausted. Pipeline Draining.")
                        break

                    payload_batch: List[ProductPayload] = []
                    for p in products:
                        payload = ProductPayload(
                            id=p.id,
                            name=p.name,
                            price=float(p.price) if p.price else 0.0,
                            description=p.description or "",
                            category=p.category or "general",
                            rating=float(p.rating) if p.rating else 0.0,
                            image_url=p.image_url
                        )
                        payload_batch.append(payload)

                    # Route to consumers. Backpressure implicitly handled by queue maxsize.
                    await os_queue.put(payload_batch)
                    await milvus_queue.put(payload_batch)

                    last_seen_id = payload_batch[-1].id
                    self.metrics.fetched += len(payload_batch)
                    self.checkpoint.commit(last_seen_id)

                    if self.metrics.fetched % 5000 == 0:
                        logger.info(f"📥 Harvester Checkpoint: {self.metrics.fetched:,} records routed.")

        except Exception as e:
            logger.critical(f"Fatal Harvester Error: {e}", exc_info=True)
            self._stop_event.set()
        finally:
            # Poison pills to signal queue exhaustion to workers
            for _ in range(self.os_workers):
                await os_queue.put(None)
            for _ in range(self.milvus_workers):
                await milvus_queue.put(None)

    async def _os_worker(self, worker_id: int, queue: asyncio.Queue) -> None:
        """Sinks domain objects into OpenSearch for keyword indexing."""
        logger.info(f"⚡ OpenSearch Worker {worker_id} Online.")
        while not self._stop_event.is_set():
            batch: Optional[List[ProductPayload]] = await queue.get()
            if batch is None:
                queue.task_done()
                break

            os_docs = [{
                "_index": self.os_index,
                "_id": str(p.id),
                "_source": {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "description": p.description,
                    "category": p.category,
                    "rating": p.rating,
                    "image_url": p.image_url
                }
            } for p in batch]

            try:
                success, failed = await helpers.async_bulk(
                    self.os_client, os_docs, chunk_size=self.os_batch_size, raise_on_error=False
                )
                self.metrics.os_success += success
                self.metrics.os_failed += len(failed)
                if failed:
                    logger.warning(f"OS Worker {worker_id} partial rejection: {len(failed)} documents.")
            except Exception as e:
                logger.error(f"OS Sink Failure on Worker {worker_id}: {e}")
                self.metrics.os_failed += len(batch)
            finally:
                queue.task_done()

    async def _milvus_worker(self, worker_id: int, queue: asyncio.Queue) -> None:
        """Sinks domain objects through the compute inference engine into Milvus."""
        logger.info(f"🧠 Milvus Cognitive Worker {worker_id} Online.")
        loop = asyncio.get_running_loop()

        # ClientSession scoped to worker to reuse HTTP connections
        async with aiohttp.ClientSession() as http_session:
            while not self._stop_event.is_set():
                batch: Optional[List[ProductPayload]] = await queue.get()
                if batch is None:
                    queue.task_done()
                    break

                for i in range(0, len(batch), self.milvus_batch_size):
                    chunk = batch[i:i + self.milvus_batch_size]

                    try:
                        # 1. TEXT PIPELINE
                        texts = [p.semantic_text for p in chunk]
                        text_vectors = await loop.run_in_executor(
                            self._thread_pool, self.inference_engine.encode_text_batch, texts
                        )

                        text_payloads = [
                            {
                                "id": p.id,
                                "vector": text_vectors[idx],
                                "price": p.price,
                                "rating": p.rating,
                                "category": p.category
                            } for idx, p in enumerate(chunk)
                        ]

                        await loop.run_in_executor(
                            self._thread_pool, lambda: self.milvus_client.insert(self.milvus_text_col, text_payloads)
                        )
                        self.metrics.milvus_text_success += len(text_payloads)

                        # 2. VISION PIPELINE
                        if self.inference_engine.vision_enabled:
                            # Concurrently fetch bytes
                            fetch_tasks = [self._download_image(http_session, p.image_url) for p in chunk]
                            image_bytes_list = await asyncio.gather(*fetch_tasks)

                            # Offload tensor math to thread pool
                            compute_tasks = []
                            for img_bytes in image_bytes_list:
                                if img_bytes:
                                    compute_tasks.append(
                                        loop.run_in_executor(self._thread_pool, self.inference_engine.encode_image, img_bytes)
                                    )
                                else:
                                    compute_tasks.append(asyncio.sleep(0, result=None)) # Identity wrapper for None

                            vis_vectors = await asyncio.gather(*compute_tasks)

                            vis_payloads = [
                                {"id": chunk[idx].id, "image_vector": vec}
                                for idx, vec in enumerate(vis_vectors) if vec is not None
                            ]

                            if vis_payloads:
                                await loop.run_in_executor(
                                    self._thread_pool, lambda: self.milvus_client.insert(self.milvus_vis_col, vis_payloads)
                                )
                                self.metrics.milvus_vis_success += len(vis_payloads)

                    except Exception as e:
                        logger.error(f"Milvus pipeline computation/insertion failure: {e}", exc_info=True)
                        self.metrics.milvus_failed += len(chunk)

                queue.task_done()

    # --- LIFECYCLE MANAGEMENT ---

    def handle_signal(self, signum: int, frame: Any) -> None:
        """Interrupt hook for graceful termination."""
        logger.warning(f"Received termination signal ({signum}). Initiating graceful shutdown...")
        self._stop_event.set()

    async def execute(self) -> None:
        """Main orchestrator execution wrapper."""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

        self.metrics.start_time = asyncio.get_running_loop().time()

        os_queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_max_size)
        milvus_queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_max_size)

        producer_task = asyncio.create_task(self._producer(os_queue, milvus_queue))

        worker_tasks = []
        for i in range(self.os_workers):
            worker_tasks.append(asyncio.create_task(self._os_worker(i, os_queue)))
        for i in range(self.milvus_workers):
            worker_tasks.append(asyncio.create_task(self._milvus_worker(i, milvus_queue)))

        # Await completion
        await producer_task

        if not self._stop_event.is_set():
            logger.info("Producer complete. Awaiting queue exhaustion...")
            await os_queue.join()
            await milvus_queue.join()

        # Gather workers gracefully
        await asyncio.gather(*worker_tasks, return_exceptions=True)

        self._teardown()

    def _teardown(self) -> None:
        """Deterministic resource release."""
        duration = asyncio.get_running_loop().time() - self.metrics.start_time

        self._thread_pool.shutdown(wait=True)

        # Client closures
        try:
            asyncio.create_task(self.os_client.close())
            asyncio.create_task(self.db_engine.dispose())
            # MilvusClient sync closure
            self.milvus_client.close()
        except Exception as e:
            logger.error(f"Non-critical failure during resource teardown: {e}")

        # Idempotent Checkpoint Clear on Success
        if not self._stop_event.is_set() and self.metrics.fetched > 0:
            self.checkpoint.clear()

        logger.info(f"""
        ====================================================
        💎 DIAMOND PIPELINE SYNCHRONIZATION COMPLETE
        ====================================================
        ⏱️  Duration:           {duration:.2f}s
        📦 Processed Records:  {self.metrics.fetched:,}
        ✅ OpenSearch Updates: {self.metrics.os_success:,}
        ✅ Semantic Vectors:   {self.metrics.milvus_text_success:,}
        ✅ Vision Vectors:     {self.metrics.milvus_vis_success:,}
        ❌ Failed Operations:  {(self.metrics.os_failed + self.metrics.milvus_failed):,}
        ====================================================
        """)


if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    synchronizer = UnifiedSyncPipeline()
    asyncio.run(synchronizer.execute())
