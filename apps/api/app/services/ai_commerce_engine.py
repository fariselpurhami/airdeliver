# apps/api/app/services/ai_commerce_engine.py

import re
import time
import os
import asyncio
import logging
import numpy as np
from fastapi import Depends
from sqlmodel import select, or_, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient, DataType
from sentence_transformers import SentenceTransformer
from app.core.config import get_core_settings, CoreSettings
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger(__name__)

# ============================================================================
# --- 1. GLOBAL SINGLETON ARCHITECTURE (The Brain Manager) ---
# ============================================================================

class AIModelSingleton:
    """
    Architectural Singleton to hold the AI Model in RAM globally.
    Ensures the model is loaded EXACTLY ONCE during the application lifecycle.
    """
    _instance = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModelSingleton, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        """Loads the model into memory if not already loaded."""
        if self._model is not None:
            return self._model

        model_path = os.getenv("EMBEDDING_MODEL_PATH", "all-MiniLM-L6-v2")
        logger.info(f"🏗️  GLOBAL ARCHITECTURE: Loading AI Brain into Shared Memory from: {model_path}...")
        
        try:
        
            if os.path.exists(model_path):
                logger.info(f"📂 Model Path Check OK. Contents: {len(os.listdir(model_path))} files found.")
            else:
                logger.warning(f"⚠️ Model path not found locally, downloading from HuggingFace: {model_path}")

            start_time = time.time()
            self._model = SentenceTransformer(model_path)
            self._model.encode(["warmup"]) 
            elapsed = time.time() - start_time
            
            logger.info(f"✅ AI Brain Loaded Successfully in {elapsed:.2f}s. Ready for Millions of Requests.")
        except Exception as e:
            logger.critical(f"🔥 FATAL: Failed to load AI Model. System cannot function. Error: {e}")
            raise e
        
        return self._model

    def get_model(self) -> SentenceTransformer:
        """Returns the cached model. Initializes if somehow missing."""
        if self._model is None:
            return self.load_model()
        return self._model

ai_manager = AIModelSingleton()


# ============================================================================
# --- 2. LOGIC ENGINE (Stateless Processor) ---
# ============================================================================

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
        self.intent_collection = "airdeliver_intents"
        
        self.direct_confirm = {"confirm order", "checkout", "confirm", "pay"}
        self.direct_clear = {"clear cart", "empty cart"}

        self._ensure_intent_knowledge_base()

    def _ensure_intent_knowledge_base(self):
        try:
            
            if self.milvus_client.has_collection(self.intent_collection):
        
                self.milvus_client.drop_collection(self.intent_collection)

            logger.info("🚀 Hydrating Intent Vector Database (Cold Start)...")

            schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
            schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=384)
            schema.add_field(field_name="intent_label", datatype=DataType.VARCHAR, max_length=64)

            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(field_name="vector", index_type="FLAT", metric_type="L2")

            self.milvus_client.create_collection(
                collection_name=self.intent_collection,
                schema=schema,
                index_params=index_params
            )

            intent_map = {
                "ADD_TO_CART": ["add to cart", "buy this", "i want to purchase", "get it", "add to bag", "grab this", "need this"],
                "REMOVE_FROM_CART": ["remove item", "delete from cart", "take it out", "don't want it", "remove this"],
                "CONFIRM_ORDER": ["checkout", "confirm order", "pay now", "finish order", "place order", "done shopping"],
                "CLEAR_CART": ["empty cart", "clear basket", "remove everything", "reset cart", "delete all"],
                "SEARCH_PRODUCT": ["find", "search", "show me", "looking for", "suggest", "recommend", "do you have"],
                "PRODUCT_QUERY": [
                    "what are the specs of", "tell me about", "features of", "battery life of",
                    "how fast is", "is it waterproof", "does it have", "why should i buy",
                    "details about", "is this good for", "description of"
                ]
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
            self.milvus_client.load_collection(collection_name=self.intent_collection)
            logger.info(f"✅ Intent Knowledge Base Ready with {len(data_rows)} anchors.")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Intent Knowledge Base: {e}")

    def _classify_intent_semantic(self, message: str) -> str:
    
        msg_lower = message.lower()

        buy_triggers = ["add ", "buy ", "get ", "i want ", "purchase ", "grab ", "take "]
        if any(msg_lower.startswith(t) for t in buy_triggers):
            return "ADD_TO_CART"

        if msg_lower in self.direct_clear:
            return "CLEAR_CART"

        if msg_lower in self.direct_confirm:
            return "CONFIRM_ORDER"

        specs_triggers = [
            "spec", "battery", "feature", "detail", "review", "desc", 
            "how fast", "waterproof", "screen", "display", "cpu", "ram",
            "wha", "wht", "what", "tell me", "info" 
        ]

        if any(w in msg_lower for w in specs_triggers) and len(message.split()) > 2:
            return "PRODUCT_QUERY"

        try:
            vector = self.embedding_model.encode([message], convert_to_numpy=True)
            results = self.milvus_client.search(
                collection_name=self.intent_collection,
                data=vector,
                limit=1,
                output_fields=["intent_label"],
                search_params={"metric_type": "L2", "params": {"nprobe": 10}}
            )

            if not results or not results[0]:
                return "SEARCH_PRODUCT"

            top_match = results[0][0]
            if top_match['distance'] > 1.1: 
                return "SEARCH_PRODUCT"

            return top_match['entity']['intent_label']
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "SEARCH_PRODUCT"

    def _normalize_message(self, message: str) -> str:
        return re.sub(r"[^\w\s]", "", message.lower())

    def _extract_intent_and_entity(self, message: str) -> Tuple[str, str]:
        normalized = self._normalize_message(message)

        intent = self._classify_intent_semantic(message)

        if intent == "ADD_TO_CART":
            clean_entity = normalized
            remove_phrases = sorted([
                "add to cart", "add to bag", "add to basket",
                "i want to buy", "i want to purchase", "i want", "i need",
                "buy", "get", "add", "purchase", "grab", "take"
            ], key=len, reverse=True)

            for phrase in remove_phrases:
                if clean_entity.startswith(phrase):
                    clean_entity = clean_entity[len(phrase):].strip()
                    break 

            return intent, clean_entity
        
        if intent == "PRODUCT_QUERY":
            
            clean_entity = message.lower()
            noise_phrases = [
                "what is", "what are", "the specs of", "specs for", "tell me about", 
                "features of", "details on", "how is the", "battery of", "show me"
            ]
            for phrase in noise_phrases:
                clean_entity = clean_entity.replace(phrase, "")
            return intent, clean_entity.strip()

        return intent, normalized

    def _get_query_embedding(self, query: str) -> List[float]:
        try:
            vector = self.embedding_model.encode(query, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    async def ensure_opensearch_index(self):
        """
        [ARCHITECTURAL SELF-HEALING]
        Automatically creates the search index if it's missing (e.g., after a fresh deploy).
        """
        index_name = "airdeliver_products"
        try:
            exists = await self.opensearch_client.indices.exists(index=index_name)

            if exists:
                logger.info(f"✅ OpenSearch Index '{index_name}' exists.")
                return

            logger.warning(f"⚠️ Index '{index_name}' missing. Creating with optimized schema...")

            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    },
                    "analysis": {
                        "analyzer": {
                            "default": {
                                "type": "standard"  
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "text", "boost": 3}, 
                        "description": {"type": "text"},
                        "category": {"type": "keyword"},
                        "price": {"type": "float"},
                        "tags": {"type": "text", "boost": 2},
                        "rating": {"type": "float"},
                        "image": {"type": "text"}
                    }
                }
            }

            await self.opensearch_client.indices.create(index=index_name, body=index_body)
            logger.info(f"✅ OpenSearch Index '{index_name}' created successfully.")

        except Exception as e:
            logger.error(f"❌ Failed to ensure OpenSearch index: {e}")

    async def _search_opensearch(self, query: str, limit: int = 50) -> List[Tuple[str, float]]:
        opensearch_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^4", "description^2", "category^3", "tags"],
                    "fuzziness": "AUTO"
                }
            },
            "size": limit,
            "_source": False
        }
        try:
            response = await self.opensearch_client.search(
                index="airdeliver_products", body=opensearch_query
            )
            return [(hit["_id"], hit["_score"]) for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.warning(f"OpenSearch query failed: {e}")
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
        except Exception as e:
            logger.warning(f"Milvus search failed: {e}")
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

    async def find_products_from_message(
        self, db: AsyncSession, message: str, user_id: int
    ) -> Tuple[List[Product], Dict[str, Any]]:
        intent, entity = self._extract_intent_and_entity(message)

        base_metadata = {"intent": intent, "entities": [entity] if entity else [], "query": message}

        if intent == "CONFIRM_ORDER": return [], base_metadata
        if intent == "CLEAR_CART": return [], base_metadata

        if intent == "ADD_TO_CART":
            remove_words = ["add", "to", "cart", "buy", "get", "purchase", "i", "want"]
            for word in remove_words:
                entity = re.sub(r'\b' + word + r'\b', '', entity, flags=re.IGNORECASE)
            entity = entity.strip()
            base_metadata["entities"] = [entity] if entity else []

        if not entity:
             statement = select(Product).order_by(func.random()).limit(50)
             return (await db.exec(statement)).all(), base_metadata

        query_vector = self._get_query_embedding(entity)

        opensearch_results, milvus_results = await asyncio.gather(
            self._search_opensearch(entity, limit=50),
            self._search_milvus(query_vector, limit=50),
            return_exceptions=True
        )

        opensearch_results = opensearch_results if isinstance(opensearch_results, list) else []
        milvus_results = milvus_results if isinstance(milvus_results, list) else []

        all_results = opensearch_results + milvus_results
        reranked_scores = self.reranker.rerank(all_results)
        sorted_ids = sorted(reranked_scores, key=reranked_scores.get, reverse=True)[:50]

        products = []
        if sorted_ids:
            product_ids_int = [int(pid) for pid in sorted_ids]
            statement = select(Product).where(Product.id.in_(product_ids_int))
            products_db = (await db.exec(statement)).all()
            product_map = {p.id: p for p in products_db}
            products = [product_map[pid] for pid in product_ids_int if pid in product_map]

        if not products:
            products = await self._fallback_sql_search(db, entity)

        base_metadata["quantity"] = 1
        return products, base_metadata

    async def find_complementary_products(
        self, db: AsyncSession, anchor_product: Product, limit: int = 20
    ) -> List[Product]:
        semantic_query = f"compatible accessories, essential add-ons, matching items for {anchor_product.name}"
        vector = self._get_query_embedding(semantic_query)
        milvus_results = await self._search_milvus(vector, limit=100, exclude_id=anchor_product.id)

        if not milvus_results:
            statement = select(Product).where(Product.id != anchor_product.id).order_by(func.random()).limit(limit)
            return (await db.exec(statement)).all()

        related_ids = [int(pid) for pid, score in milvus_results]
        statement = select(Product).where(Product.id.in_(related_ids))
        products = (await db.exec(statement)).all()

        product_map = {p.id: p for p in products}
        ordered_products = []
        seen_names = set()

        for pid in related_ids:
            if pid in product_map:
                p = product_map[pid]
                if p.name not in seen_names:
                    ordered_products.append(p)
                    seen_names.add(p.name)

        return ordered_products[:limit]

    async def generate_smart_bundle(
        self, db: AsyncSession, anchor_product: Product
    ) -> List[Product]:
        bundle_query = f"best value accessories and addons for {anchor_product.name}"
        vector = self._get_query_embedding(bundle_query)
        milvus_results = await self._search_milvus(vector, limit=50, exclude_id=anchor_product.id)

        if not milvus_results:
            return []

        related_ids = [int(pid) for pid, score in milvus_results]
        statement = select(Product).where(Product.id.in_(related_ids))
        products = (await db.exec(statement)).all()

        product_map = {p.id: p for p in products}
        bundle_items = []

        for pid in related_ids:
            if pid in product_map:
                p = product_map[pid]
                if p.price < anchor_product.price * 0.7:
                    bundle_items.append(p)
                    if len(bundle_items) >= 3: break

        return bundle_items

# ============================================================================
# --- 3. DEPENDENCY INJECTION (Optimized) ---
# ============================================================================

def get_embedding_model() -> SentenceTransformer:
    """
    Dependency to return the Pre-Loaded AI Model.
    This executes in MICROSECONDS because the model is already in RAM.
    """
    return ai_manager.get_model()

def get_milvus_client(settings: CoreSettings = Depends(get_core_settings)) -> MilvusClient:
    """
    Retries removed for request path.
    Ideally, connection should be established at startup, but MilvusClient is lightweight wrapper.
    """
    if not isinstance(settings, CoreSettings):
        settings = get_core_settings()

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
    """
    Factory to create the Engine with dependencies injected.
    The 'embedding_model' here is the GLOBAL SINGLETON instance.
    """
    return AICommerceEngine(opensearch_client, milvus_client, embedding_model)
