# //** apps/api/app/services/ai_commerce_engine.py **//

import re
import asyncio
import logging
import json
from fastapi import Depends
from sqlmodel import select, or_, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
from app.core.config import get_core_settings, CoreSettings
from app.services.cache_service import IAsyncCacheClient

logger = logging.getLogger(__name__)

MILVUS_DB_PATH = "/data/storage/milvus_in_memory.db"

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
        
        self.intent_patterns = {
            "ADD_TO_CART": [re.compile(p) for p in [r"add (.*) to (cart|bag)", r"buy (.*)", r"i want (.*)", r"get (.*)", r"purchase (.*)"]],
            "REMOVE_FROM_CART": [re.compile(p) for p in [r"remove (.*)", r"delete (.*)", r"take off (.*)"]],
            "SEARCH_PRODUCT": [re.compile(p) for p in [r"find (.*)", r"search for (.*)", r"show me (.*)", r"do you have (.*)", r"looking for (.*)", r"need (.*)", r"suggest (.*)", r"recommend (.*)"]],
             "CONFIRM_ORDER": [re.compile(p) for p in [r"confirm", r"checkout", r"pay", r"finish"]],
             "CLEAR_CART": [re.compile(p) for p in [r"clear cart", r"empty cart", r"reset"]],
        }
        self.direct_confirm = {"confirm order", "checkout", "confirm"}
        self.direct_clear = {"clear cart", "empty cart"}

    def _normalize_message(self, message: str) -> str:
    
        return re.sub(r"[^\w\s]", "", message.lower())

    def _extract_intent_and_entity(self, message: str) -> Tuple[str, str]:
        normalized = self._normalize_message(message)
        
        if normalized in self.direct_confirm: return "CONFIRM_ORDER", ""
        if normalized in self.direct_clear: return "CLEAR_CART", ""

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = pattern.search(normalized)
                if match:
                    return intent, match.group(1).strip() if match.groups() else ""
        
        return "SEARCH_PRODUCT", normalized

    def _get_query_embedding(self, query: str) -> List[float]:
        try:
            vector = self.embedding_model.encode(query, convert_to_numpy=True)
            return vector.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []

    async def _search_opensearch(self, query: str, limit: int = 20) -> List[Tuple[str, float]]:
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
            logger.warning(f"OpenSearch failed: {e}")
            return []

    async def _search_milvus(self, vector: List[float], limit: int = 20, exclude_id: Optional[int] = None) -> List[Tuple[str, float]]:
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

        if not entity:

             statement = select(Product).order_by(func.random()).limit(10)
             return (await db.exec(statement)).all(), {"intent": intent}

        query_vector = self._get_query_embedding(entity)
        
        opensearch_results, milvus_results = await asyncio.gather(
            self._search_opensearch(entity, limit=30),
            self._search_milvus(query_vector, limit=30),
            return_exceptions=True
        )

        opensearch_results = opensearch_results if isinstance(opensearch_results, list) else []
        milvus_results = milvus_results if isinstance(milvus_results, list) else []

        all_results = opensearch_results + milvus_results
        reranked_scores = self.reranker.rerank(all_results)
        sorted_ids = sorted(reranked_scores, key=reranked_scores.get, reverse=True)[:20]

        products = []
        if sorted_ids:
            product_ids_int = [int(pid) for pid in sorted_ids]
        
            statement = select(Product).where(Product.id.in_(product_ids_int))
            products_db = (await db.exec(statement)).all()
            
            product_map = {p.id: p for p in products_db}
            products = [product_map[pid] for pid in product_ids_int if pid in product_map]

        if not products:
            logger.info(f"Hybrid search yielded 0 results for '{entity}'. Falling back to SQL.")
            products = await self._fallback_sql_search(db, entity)

        return products, {"intent": intent, "quantity": 1}

    async def find_complementary_products(
        self, db: AsyncSession, anchor_product: Product, limit: int = 20
    ) -> List[Product]:
        rich_text = f"{anchor_product.category} accessories for {anchor_product.name} {anchor_product.description}"
        vector = self._get_query_embedding(rich_text)

        milvus_results = await self._search_milvus(vector, limit=50, exclude_id=anchor_product.id)
        
        if not milvus_results:
            statement = select(Product).where(
                and_(Product.category == anchor_product.category, Product.id != anchor_product.id)
            ).limit(limit)
            return (await db.exec(statement)).all()

        related_ids = [int(pid) for pid, score in milvus_results]
        statement = select(Product).where(Product.id.in_(related_ids))
        products = (await db.exec(statement)).all()
        
        product_map = {p.id: p for p in products}
        ordered_products = [product_map[pid] for pid in related_ids if pid in product_map]
        
        return ordered_products[:limit]

def get_embedding_model() -> SentenceTransformer:

    return SentenceTransformer("all-MiniLM-L6-v2")

def get_milvus_client() -> MilvusClient:
    return MilvusClient(uri=MILVUS_DB_PATH)

async def get_opensearch_client(settings: CoreSettings = Depends(get_core_settings)) -> AsyncGenerator[AsyncOpenSearch, None]:
    hosts = [{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}]
    auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASS) if settings.APP_ENV == "production" else None
    client = AsyncOpenSearch(hosts=hosts, http_auth=auth, use_ssl=False, verify_certs=False, ssl_assert_hostname=False, ssl_show_warn=False)
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
