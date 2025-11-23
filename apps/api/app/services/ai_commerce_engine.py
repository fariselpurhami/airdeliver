# apps/api/app/services/ai_commerce_engine.py

import re
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
from pymilvus import MilvusClient, DataType, MilvusException
from sentence_transformers import SentenceTransformer
from app.core.config import get_core_settings, CoreSettings
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger(__name__)

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
                logger.info("🧠 Semantic Intent Knowledge Base found.")
                return

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
                "SEARCH_PRODUCT": ["find", "search", "show me", "looking for", "suggest", "recommend", "do you have"]
            }

            data_rows = []
            for label, phrases in intent_map.items():
                vectors = self.embedding_model.encode(phrases, convert_to_numpy=True)
                for vec in vectors:
                    data_rows.append({"vector": vec, "intent_label": label})

            self.milvus_client.insert(collection_name=self.intent_collection, data=data_rows)
            self.milvus_client.flush(collection_name=self.intent_collection)
            self.milvus_client.load_collection(collection_name=self.intent_collection)

            logger.info(f"✅ Intent Knowledge Base Ready with {len(data_rows)} semantic anchors.")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Intent Knowledge Base: {e}")

    def _classify_intent_semantic(self, message: str) -> str:
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
            
            if top_match['distance'] > 0.9:
                return "SEARCH_PRODUCT"

            return top_match['entity']['intent_label']
        except Exception as e:
            logger.warning(f"Intent classification failed (using fallback): {e}")
            return "SEARCH_PRODUCT"

    def _normalize_message(self, message: str) -> str:
        return re.sub(r"[^\w\s]", "", message.lower())

    def _extract_intent_and_entity(self, message: str) -> Tuple[str, str]:
        normalized = self._normalize_message(message)

        if normalized in self.direct_confirm: return "CONFIRM_ORDER", ""
        if normalized in self.direct_clear: return "CLEAR_CART", ""

        intent = self._classify_intent_semantic(message)

        return intent, normalized

    def _get_query_embedding(self, query: str) -> List[float]:
        try:
            vector = self.embedding_model.encode(query, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

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

        if intent == "CONFIRM_ORDER": return [], {"intent": "CONFIRM_ORDER"}
        if intent == "CLEAR_CART": return [], {"intent": "CLEAR_CART"}

        if intent == "ADD_TO_CART":
            remove_words = ["add", "to", "cart", "buy", "get", "purchase", "i", "want"]
            for word in remove_words:
                entity = re.sub(r'\b' + word + r'\b', '', entity, flags=re.IGNORECASE)
            entity = entity.strip()

        if not entity:
             statement = select(Product).order_by(func.random()).limit(50)
             return (await db.exec(statement)).all(), {"intent": intent}

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

        return products, {"intent": intent, "quantity": 1}

    async def find_complementary_products(
        self, db: AsyncSession, anchor_product: Product, limit: int = 20
    ) -> List[Product]:
        semantic_query = f"compatible accessories, essential add-ons, matching items, and complementary supplies for {anchor_product.name} in category {anchor_product.category}"
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


def get_embedding_model() -> SentenceTransformer:

    return SentenceTransformer("all-MiniLM-L6-v2")

def get_milvus_client() -> MilvusClient:

    milvus_uri = os.environ.get("MILVUS_URI", "http://milvus:19530")
    try:
        client = MilvusClient(uri=milvus_uri)
        return client
    except Exception as e:
        logger.critical(f"🔥 Failed to connect to Milvus at {milvus_uri}: {e}")
        raise e

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
        timeout=5,
        max_retries=3,
        retry_on_timeout=True
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
