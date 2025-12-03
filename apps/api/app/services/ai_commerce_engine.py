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

logger = logging.getLogger("airdeliver.engine")

# ============================================================================
# --- 1. GLOBAL SINGLETON ARCHITECTURE (The Multilingual Brain) ---
# ============================================================================

class AIModelSingleton:
    """
    Architectural Singleton.
    Upgraded to support GLOBAL MULTILINGUAL EMBEDDINGS (50+ Languages).
    """
    _instance = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModelSingleton, cls).__new__(cls)
        return cls._instance

    def load_model(self):
        if self._model is not None:
            return self._model

        model_name = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")
        logger.info(f"🏗️  GLOBAL ARCHITECTURE: Loading Multilingual Brain ({model_name})...")
        
        try:
            start_time = time.time()
            self._model = SentenceTransformer(model_name)
            self._model.encode(["warmup", "تجربة", "test", "prueba"], convert_to_numpy=True)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Multilingual Brain Loaded in {elapsed:.2f}s. Ready for Global Traffic.")
        except Exception as e:
            logger.critical(f"🔥 FATAL: Failed to load AI Model. Error: {e}")
            raise e
        
        return self._model

    def get_model(self) -> SentenceTransformer:
        if self._model is None:
            return self.load_model()
        return self._model

ai_manager = AIModelSingleton()


# ============================================================================
# --- 2. LOGIC ENGINE (Stateless Processor) ---
# ============================================================================

class HybridSearchReranker:
    """
    Reciprocal Rank Fusion (RRF) Algorithm.
    Combines Keyword Scores (OpenSearch) with Vector Scores (Milvus) fairly.
    """
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
        
        self.direct_confirm = {"confirm order", "checkout", "pay", "تأكيد الطلب", "دفع", "انهاء الشراء", "شراء"}
        self.direct_clear = {"clear cart", "empty cart", "تفريغ السلة", "مسح الكارت", "حذف الكل"}

        self._ensure_intent_knowledge_base()

    def _ensure_intent_knowledge_base(self):
        """
        Hydrates the Vector DB with Multilingual Intent Anchors.
        Ensures 'اشتري' maps to the same mathematical point as 'Buy'.
        """
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

            self.milvus_client.create_collection(
                collection_name=self.intent_collection,
                schema=schema,
                index_params=index_params
            )

            intent_map = {
                "ADD_TO_CART": [
                    "add to cart", "buy this", "get it", "purchase", 
                    "ضيف للسلة", "اشتري ده", "عايز اشتري", "حط في الكارت", "شراء",
                    "ajouter au panier", "acheter", "añadir al carrito", "comprar"
                ],
                "REMOVE_FROM_CART": [
                    "remove item", "delete", "take it out", 
                    "امسح ده", "شيل من السلة", "احذف", "مش عايزه",
                    "retirer", "supprimer", "eliminar"
                ],
                "CONFIRM_ORDER": [
                    "checkout", "confirm order", "pay now", 
                    "دفع", "تأكيد الطلب", "خلاص اشتري", "حاسب",
                    "payer", "commander", "pagar", "confirmar"
                ],
                "CLEAR_CART": [
                    "empty cart", "clear all", 
                    "فضي السلة", "مسح الكل", "ريست",
                    "vider le panier", "vaciar carrito"
                ],
                "SEARCH_PRODUCT": [
                    "find", "search", "show me", 
                    "ابحث عن", "وريني", "عايز اشوف", "عندك",
                    "trouver", "chercher", "buscar"
                ],
                "PRODUCT_QUERY": [
                    "specs", "features", "details", "is it good", 
                    "مواصفات", "تفاصيل", "هل ده كويس", "ينفع لـ", "مميزات", "عيوب",
                    "spécifications", "caractéristiques", "detalles"
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
            logger.info(f"✅ Multilingual Intent Base Ready ({len(data_rows)} anchors).")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Intent Knowledge Base: {e}")

    def _classify_intent_semantic(self, message: str) -> str:
        msg_lower = message.lower().strip()

        if any(w in msg_lower for w in ["add", "buy", "ضيف", "اشتري", "هات", "شراء"]):
            return "ADD_TO_CART"
        if msg_lower in self.direct_confirm:
            return "CONFIRM_ORDER"

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
            
            if top_match['distance'] > 1.3: 
                return "SEARCH_PRODUCT"

            return top_match['entity']['intent_label']
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")
            return "SEARCH_PRODUCT"

    def _extract_intent_and_entity(self, message: str) -> Tuple[str, str]:
        intent = self._classify_intent_semantic(message)
        
        clean_entity = message
        
        if intent == "ADD_TO_CART":
            
            triggers = [
                "add to cart", "buy", "get", "purchase", 
                "ضيف", "اشتري", "عايز", "هات", 
                "ajouter", "acheter", "comprar"
            ]
            for t in triggers:
                clean_entity = re.sub(t, "", clean_entity, flags=re.IGNORECASE)
        
        elif intent == "PRODUCT_QUERY":
            triggers = ["specs", "details", "mowasfat", "مواصفات", "تفاصيل", "info"]
            for t in triggers:
                clean_entity = re.sub(t, "", clean_entity, flags=re.IGNORECASE)

        return intent, clean_entity.strip()

    def _get_query_embedding(self, query: str) -> List[float]:
        try:
            vector = self.embedding_model.encode(query, convert_to_numpy=True)
            return vector.tolist()
        except Exception:
            return []

    async def ensure_opensearch_index(self):
        """Self-healing index creation with standard analyzer"""
        index_name = "airdeliver_products"
        try:
            exists = await self.opensearch_client.indices.exists(index=index_name)
            if exists: return

            index_body = {
                "settings": {
                    "index": { "number_of_shards": 1, "number_of_replicas": 0 }
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
                        "image_url": {"type": "text"}
                    }
                }
            }
            await self.opensearch_client.indices.create(index=index_name, body=index_body)
            logger.info(f"✅ OpenSearch Index '{index_name}' created.")
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

    async def find_products_from_message(
        self, db: AsyncSession, message: str, user_id: int
    ) -> Tuple[List[Product], Dict[str, Any]]:
        """
        GLOBAL SEARCH ROUTER.
        1. Identifies Intent (in any language).
        2. Extracts Entity (Product Name).
        3. Performs Hybrid Search (Vector + Text).
        4. Reranks results.
        """
        intent, entity = self._extract_intent_and_entity(message)
        
        base_metadata = {"intent": intent, "entities": [entity] if entity else [], "query": message}

        if intent in ["CONFIRM_ORDER", "CLEAR_CART"]: 
            return [], base_metadata

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

    async def find_complementary_products(self, db: AsyncSession, anchor_product: Product, limit: int = 20) -> List[Product]:
         semantic_query = f"accessories for {anchor_product.name}" 
         vector = self._get_query_embedding(semantic_query)
         milvus_results = await self._search_milvus(vector, limit=100, exclude_id=anchor_product.id)
         
         if not milvus_results: return []
         
         related_ids = [int(pid) for pid, score in milvus_results]
         statement = select(Product).where(Product.id.in_(related_ids))
         products = (await db.exec(statement)).all()
         return products[:limit]

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
                if p.price < anchor_product.price * 0.7:
                    bundle_items.append(p)
                    if len(bundle_items) >= 3: break
        return bundle_items

# ============================================================================
# --- 3. DEPENDENCY INJECTION ---
# ============================================================================

def get_embedding_model() -> SentenceTransformer:
    return ai_manager.get_model()

def get_milvus_client(settings: CoreSettings = Depends(get_core_settings)) -> MilvusClient:

    if not isinstance(settings, CoreSettings):
        settings = get_core_settings()

    return MilvusClient(uri=settings.MILVUS_URI)

async def get_opensearch_client(settings: CoreSettings = Depends(get_core_settings)) -> AsyncGenerator[AsyncOpenSearch, None]:

    if not isinstance(settings, CoreSettings):
        settings = get_core_settings()

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
