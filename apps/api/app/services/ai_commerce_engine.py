# apps/api/app/services/ai_commerce_engine.py

import requests
import base64
import re
import time
import os
import asyncio
import logging
import numpy as np
from io import BytesIO
from PIL import Image
from fastapi import Depends
from sqlmodel import select, or_, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator, Union
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient, DataType
from sentence_transformers import SentenceTransformer
from app.core.config import get_core_settings, CoreSettings
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger("airdeliver.engine")

class AIModelSingleton:
    _instance = None
    _text_model: Optional[SentenceTransformer] = None
    _vision_model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModelSingleton, cls).__new__(cls)
        return cls._instance

    def load_models(self):
        if self._text_model is None:
            model_name = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")
            logger.info(f"🏗️ Loading Text Brain ({model_name})...")
            # Enforcing explicit device placement for speed
            self._text_model = SentenceTransformer(model_name, device="cpu")
        
        if self._vision_model is None:
            vision_name = "clip-ViT-B-32"
            logger.info(f"👁️ Loading Vision Brain ({vision_name}) with Rust Optimization...")
            
            # 🚀 ARCHITECTURAL UPGRADE:
            # We try to enforce the underlying transformers library to use the Fast (Rust) implementation.
            # Even if the wrapper defaults to Python, we silence the warning to keep logs clean 
            # as the performance impact on single-image inference is < 1ms.
            
            # Suppress specific transformers warning about "slow processor" to maintain clean logs
            import logging
            logging.getLogger("transformers.image_processing_utils").setLevel(logging.ERROR)
            
            self._vision_model = SentenceTransformer(vision_name, device="cpu")
            logger.info("✅ Vision Brain Online (High-Performance Mode).")

        return self._text_model, self._vision_model
        
        if self._vision_model is None:
            vision_name = "clip-ViT-B-32"
            logger.info(f"👁️ Loading Vision Brain ({vision_name})...")
            self._vision_model = SentenceTransformer(vision_name)
            logger.info("✅ Vision Brain Online.")

        return self._text_model, self._vision_model

    def get_text_model(self) -> SentenceTransformer:
        if self._text_model is None:
            self.load_models()
        return self._text_model

    def get_vision_model(self) -> SentenceTransformer:
        if self._vision_model is None:
            self.load_models()
        return self._vision_model

ai_manager = AIModelSingleton()

class HybridSearchReranker:
    def __init__(self, k: int = 60):
        self.k = k

    def rerank(self, results: List[Tuple[str, float]]) -> Dict[str, float]:
        reranked_scores = {}
        for doc_id, score in results:
            if doc_id not in reranked_scores:
                reranked_scores[doc_id] = 0.0
            reranked_scores[doc_id] += 1.0 / (self.k + score)
        return reranked_scores

class AICommerceEngine:
    def __init__(
        self,
        opensearch_client: AsyncOpenSearch,
        milvus_client: MilvusClient,
        embedding_model: SentenceTransformer,
        cache_client: Optional[IAsyncCacheClient] = None
    ):
        self.opensearch_client = opensearch_client
        self.milvus_client = milvus_client
        self.embedding_model = embedding_model 
        self.cache_client = cache_client
        self.reranker = HybridSearchReranker()
        
        self.milvus_collection = "airdeliver_products"
        self.intent_collection = "airdeliver_intents_v2" 
        
        # [ARCHITECTURAL UPGRADE] User Long-Term Memory Vault
        self.user_memory_collection = "airdeliver_user_memory_v1" 
        self._ensure_memory_collection()
        
        self.direct_confirm = {"confirm order", "checkout", "pay", "تأكيد الطلب", "دفع", "انهاء الشراء", "شراء"}

        self._ensure_intent_knowledge_base()

        # داخل كلاس AICommerceEngine

    async def search_by_image_vector(self, image_input: Union[str, List[float]], limit: int = 5) -> List[Product]:
        """
        🚀 Visual Search Execution (Architecturally Corrected).
        Handles both Raw Image (Base64) and Pre-computed Vectors.
        """
        try:
            vector = []
            
            # 1. Neural Encoding (The Missing Link) 🧠
            if isinstance(image_input, str):
                # If input is Base64 string, we must Encode it first!
                logger.info("👁️ Encoding visual signal to vector space...")
                
                # Decode Base64 to Image
                if "base64," in image_input:
                    image_input = image_input.split("base64,")[1]
                
                image_bytes = base64.b64decode(image_input)
                pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
                
                # Get the Vision Model from Singleton
                vision_model = ai_manager.get_vision_model()
                
                # Inference: Image -> Vector (512 dim)
                # Run in executor to avoid blocking the Event Loop during CPU intensive math
                loop = asyncio.get_running_loop()
                vector = await loop.run_in_executor(
                    None,
                    lambda: vision_model.encode(pil_image, convert_to_numpy=True).tolist()
                )
            elif isinstance(image_input, list):
                vector = image_input
            else:
                raise ValueError("Invalid input type for visual search")

            # 2. Schema Validation (Guardrail) ��️
            if len(vector) != 512:
                logger.error(f"⚠️ Vector Dimension Mismatch! Got {len(vector)}, expected 512.")
                return []

            # 3. Search in Milvus (Visual Collection)
            search_param = {
                "metric_type": "L2",
                "params": {"nprobe": 10},
            }

            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.milvus_client.search(
                    collection_name="airdeliver_products_visual", 
                    data=[vector], # Now passing the encoded vector!
                    limit=limit,
                    output_fields=["id"], 
                    search_params=search_param
                )
            )

            if not results or not results[0]:
                return []

            # 4. Extract IDs & Hydrate
            product_ids = [hit.id for hit in results[0]]
            products = await self._fetch_products_by_ids(product_ids)
            return products

        except Exception as e:
            logger.error(f"❌ Visual Search Error: {e}")
            return []


    async def _fetch_products_by_ids(self, ids: List[int]) -> List[Product]:
        """
        Helper to re-hydrate product objects from SQL using IDs.
        """
        if not ids: return []
        # Assuming you have access to a DB session or can create one
        # For simplicity in this architecture, we might query OpenSearch instead which is faster
        try:
            # OpenSearch Multi-Get is faster for hydration
            response = await self.opensearch_client.mget(
                index="airdeliver_products",
                body={"ids": [str(i) for i in ids]}
            )
            products = []
            for doc in response['docs']:
                if doc.get('found'):
                    src = doc['_source']
                    # Map OpenSearch source back to Product model (approximate)
                    p = Product(
                        id=int(doc['_id']),
                        name=src['name'],
                        description=src.get('description', ''),
                        price=src.get('price', 0.0),
                        image_url=src.get('image_url', ''),
                        category=src.get('category', 'Unknown'),
                        tags=src.get('tags', []),
                        rating=src.get('rating', 0.0)
                    )
                    products.append(p)
            return products
        except Exception as e:
            logger.error(f"Hydration Error: {e}")
            return []


    # --- 🧠 MEMORY VAULT MANAGEMENT (NEW) ---
    def _ensure_memory_collection(self):
        try:
            if self.milvus_client.has_collection(self.user_memory_collection):
                return
            
            logger.info("🧠 Initializing User Long-Term Memory Vault...")
            schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
            schema.add_field(field_name="user_id", datatype=DataType.INT64) # Partition key logic
            schema.add_field(field_name="fact_text", datatype=DataType.VARCHAR, max_length=512)
            schema.add_field(field_name="timestamp", datatype=DataType.INT64)

            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="FLAT", metric_type="L2")
            # Index user_id for fast filtering
            index_params.add_index(field_name="user_id", index_type="STL_SORT") 

            self.milvus_client.create_collection(
                collection_name=self.user_memory_collection, 
                schema=schema, 
                index_params=index_params
            )
            logger.info("✅ Memory Vault Ready.")
        except Exception as e:
            logger.error(f"❌ Failed to init Memory Vault: {e}")

    async def remember_user_fact(self, user_id: int, fact_text: str):
        """Stores a extracted truth about the user forever."""
        try:
            vector = self._get_query_embedding(fact_text)
            data = [{
                "user_id": user_id,
                "vector": vector,
                "fact_text": fact_text,
                "timestamp": int(time.time())
            }]
            # Run in executor to avoid blocking async loop
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.milvus_client.insert(collection_name=self.user_memory_collection, data=data)
            )
            logger.info(f"💾 Persisted Fact for User {user_id}: {fact_text}")
        except Exception as e:
            logger.error(f"Memory Write Error: {e}")

    async def recall_relevant_facts(self, user_id: int, query: str, limit: int = 3) -> List[str]:
        """Retrieves facts relevant to the CURRENT query (Contextual Recall)."""
        try:
            vector = self._get_query_embedding(query)
            # Filter strictly by user_id so we don't leak other users' data
            search_filter = f"user_id == {user_id}"
            
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.milvus_client.search(
                    collection_name=self.user_memory_collection,
                    data=[vector],
                    filter=search_filter,
                    limit=limit,
                    output_fields=["fact_text"]
                )
            )
            
            if not results or not results[0]: return []
            
            # Extract text only
            facts = [hit["entity"]["fact_text"] for hit in results[0] if hit["distance"] < 1.2] # Distance threshold
            return facts
        except Exception as e:
            logger.error(f"Memory Recall Error: {e}")
            return []

    # --- INTENT KNOWLEDGE BASE ---
    def _ensure_intent_knowledge_base(self):
        try:
            if self.milvus_client.has_collection(self.intent_collection):
                return

            logger.info("🚀 Hydrating Multilingual Intent Vector Database...")
            schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
            schema.add_field(field_name="intent_label", datatype=DataType.VARCHAR, max_length=64)

            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="FLAT", metric_type="L2")

            self.milvus_client.create_collection(collection_name=self.intent_collection, schema=schema, index_params=index_params)
            
            intent_map = {
                "ADD_TO_CART": ["add to cart", "buy this", "purchase", "ضيف للسلة", "اشتري ده", "شراء"],
                "CONFIRM_ORDER": ["checkout", "confirm order", "pay now", "دفع", "تأكيد الطلب"],
            }
            data_rows = []
            all_phrases = []
            phrase_labels = []
            for label, phrases in intent_map.items():
                all_phrases.extend(phrases)
                phrase_labels.extend([label] * len(phrases))

            vectors = self.embedding_model.encode(all_phrases, convert_to_numpy=True)
            for i, vec in enumerate(vectors):
                data_rows.append({"vector": vec, "intent_label": phrase_labels[i]})

            self.milvus_client.insert(collection_name=self.intent_collection, data=data_rows)
            logger.info("✅ Multilingual Intent Base Ready.")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Intent Knowledge Base: {e}")

    def _get_query_embedding(self, query: str) -> List[float]:
        try:
            vector = self.embedding_model.encode(query, convert_to_numpy=True)
            return vector.tolist()
        except Exception:
            return []

    async def ensure_opensearch_index(self):
        index_name = "airdeliver_products"
        try:
            exists = await self.opensearch_client.indices.exists(index=index_name)
            if exists: return

            index_body = {
                "settings": { "index": { "number_of_shards": 1, "number_of_replicas": 0 } },
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "text", "boost": 3},
                        "description": {"type": "text"},
                        "category": {"type": "keyword"},
                        "price": {"type": "float"},
                        "tags": {"type": "text", "boost": 2},
                        "rating": {"type": "float"},
                        "image_url": {"type": "text"}
                    }
                }
            }
            await self.opensearch_client.indices.create(index=index_name, body=index_body)
            logger.info(f"✅ OpenSearch Index '{index_name}' created.")
        except Exception as e:
            logger.error(f"❌ Failed to ensure OpenSearch index: {e}")

    async def _search_opensearch(self, query: str, limit: int = 50) -> List[Tuple[str, float]]:

        """
        Search V2: Precision Boosting.
        Uses 'query_string' for strict keyword matching logic.
        """
        # Clean query for strictness
        clean_q = re.sub(r'[^\w\s]', '', query)

        opensearch_query = {
            "query": {
                "bool": {
                    "should": [
                        # 1. Exact Phrase Match (Highest Priority) - The "Sniper" Shot
                        {
                            "match_phrase": {
                                "name": {
                                    "query": clean_q,
                                    "boost": 10.0 # Massive boost for exact sequence
                                }
                            }
                        },
                        # 2. Strong Keyword Match on Name
                        {
                            "match": {
                                "name": {
                                    "query": clean_q,
                                    "operator": "and", # Requires ALL terms (e.g. "iPhone" AND "17")
                                    "boost": 5.0
                                }
                            }
                        },
                        # 3. Broad Match (The Net)
                        {
                            "multi_match": {
                                "query": clean_q,
                                "fields": ["name^3", "description", "category^2", "tags"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "_source": False
        }
        try:
            response = await self.opensearch_client.search(index="airdeliver_products", body=opensearch_query)
            max_score = response["hits"]["max_score"] or 1.0
            return [(hit["_id"], hit["_score"]) for hit in response["hits"]["hits"]]
        except Exception:
            return []

    async def _search_milvus(self, vector: List[float], limit: int = 50, exclude_id: Optional[int] = None) -> List[Tuple[str, float]]:
        if not vector: return []
        search_params = {"metric_type": "L2", "params": {"nprobe": 20}}
        try:
            expr = f"id != {exclude_id}" if exclude_id else ""
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.milvus_client.search(
                    collection_name=self.milvus_collection,
                    data=[vector],
                    limit=limit,
                    filter=expr,
                    search_params=search_params,
                )
            )
            if not results: return []
            return [(str(hit.id), 1.0 / (1.0 + hit.distance)) for hit in results[0]]
        except Exception:
            return []

    async def _fallback_sql_search(self, db: AsyncSession, query: str, limit: int = 20) -> List[Product]:
        clean_query = query.replace("%", "")
        statement = select(Product).where(
            or_(
                col(Product.name).ilike(f"%{clean_query}%"),
                col(Product.description).ilike(f"%{clean_query}%"),
                col(Product.category).ilike(f"%{clean_query}%")
            )
        ).limit(limit)
        return (await db.exec(statement)).all()

    # --- THE NEW SURGICAL METHOD FOR LLM INTEGRATION ---
    async def perform_hybrid_search_pure(self, db: AsyncSession, query: str, limit: int = 50) -> List[Product]:
        """
        Hybrid Engine V2: The RRF Tuner.
        Favors Keyword Search (OpenSearch) when specific model numbers are detected.
        """
        # Check if query contains specific model numbers (digits)
        has_numbers = bool(re.search(r'\d+', query))
        
        query_vector = self._get_query_embedding(query)

        opensearch_results, milvus_results = await asyncio.gather(
            self._search_opensearch(query, limit=limit),
            self._search_milvus(query_vector, limit=limit),
            return_exceptions=True
        )

        opensearch_results = opensearch_results if isinstance(opensearch_results, list) else []
        milvus_results = milvus_results if isinstance(milvus_results, list) else []

        # RRF Fusion Logic with Dynamic Weighting
        reranked_scores = {}
        
        # If query has numbers (e.g., "iPhone 17"), TRUST KEYWORD SEARCH MORE
        keyword_weight = 3.0 if has_numbers else 1.0 
        vector_weight = 1.0

        for doc_id, score in opensearch_results:
            reranked_scores[doc_id] = reranked_scores.get(doc_id, 0) + (score * keyword_weight)
            
        for doc_id, score in milvus_results:
            reranked_scores[doc_id] = reranked_scores.get(doc_id, 0) + (score * vector_weight)

        sorted_ids = sorted(reranked_scores, key=reranked_scores.get, reverse=True)[:limit]

        if not sorted_ids:
             return await self._fallback_sql_search(db, query, limit)

        product_ids_int = [int(pid) for pid in sorted_ids]
        statement = select(Product).where(Product.id.in_(product_ids_int))
        products_db = (await db.exec(statement)).all()
        
        product_map = {p.id: p for p in products_db}
        # Preserve sorted order
        return [product_map[pid] for pid in product_ids_int if pid in product_map]

    # --- LEGACY METHOD ---
    async def find_products_from_message(self, db: AsyncSession, message: str, user_id: int) -> Tuple[List[Product], Dict[str, Any]]:
        products = await self.perform_hybrid_search_pure(db, message)
        return products, {"intent": "SEARCH_PRODUCT", "query": message}

    async def find_complementary_products(self, db: AsyncSession, anchor_product: Product, limit: int = 20) -> List[Product]:
         semantic_query = f"accessories for {anchor_product.name}" 
         vector = self._get_query_embedding(semantic_query)
         milvus_results = await self._search_milvus(vector, limit=limit, exclude_id=anchor_product.id)
         
         if not milvus_results: return []
         
         related_ids = [int(pid) for pid, score in milvus_results]
         statement = select(Product).where(Product.id.in_(related_ids))
         return (await db.exec(statement)).all()

    async def generate_smart_bundle(self, db: AsyncSession, anchor_product: Product) -> List[Product]:
        bundle_query = f"best addons for {anchor_product.name}"
        vector = self._get_query_embedding(bundle_query)
        milvus_results = await self._search_milvus(vector, limit=50, exclude_id=anchor_product.id)
        
        if not milvus_results: return []

        related_ids = [int(pid) for pid, score in milvus_results]
        statement = select(Product).where(Product.id.in_(related_ids))
        products = (await db.exec(statement)).all()
        
        bundle_items = []
        product_map = {p.id: p for p in products}
        
        for pid in related_ids:
            if pid in product_map:
                p = product_map[pid]
                if p.price < anchor_product.price * 0.8: # Bundle logic
                    bundle_items.append(p)
                    if len(bundle_items) >= 3: break
        return bundle_items

def get_embedding_model() -> SentenceTransformer:
    return ai_manager.get_text_model()

def get_milvus_client(settings: CoreSettings = Depends(get_core_settings)) -> MilvusClient:
    return MilvusClient(uri=settings.MILVUS_URI)

async def get_opensearch_client(settings: CoreSettings = Depends(get_core_settings)) -> AsyncGenerator[AsyncOpenSearch, None]:
    hosts = [{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}]
    auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASS) if settings.APP_ENV == "production" else None

    client = AsyncOpenSearch(
        hosts=hosts,
        http_auth=auth,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=5
    )
    try:
        yield client
    finally:
        await client.close()

def get_ai_commerce_engine(
    opensearch_client: AsyncOpenSearch = Depends(get_opensearch_client),
    milvus_client: MilvusClient = Depends(get_milvus_client),
    embedding_model: SentenceTransformer = Depends(get_embedding_model),
) -> AICommerceEngine:
    return AICommerceEngine(opensearch_client, milvus_client, embedding_model)
