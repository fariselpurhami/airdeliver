# apps/api/app/services/ai_commerce_engine.py

import re
import asyncio
from fastapi import Depends
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.product import Product
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
from sqlalchemy import case, cast, String, and_
from opensearchpy import AsyncOpenSearch
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
import numpy as np
from app.core.config import get_core_settings, CoreSettings

MILVUS_DB_PATH = "/app/storage/milvus_in_memory.db"

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
    ):
        self.opensearch_client = opensearch_client
        self.milvus_client = milvus_client
        self.embedding_model = embedding_model
        self.reranker = HybridSearchReranker()
        self.milvus_collection = "airdeliver_products"
        self.intent_keywords = {
            "ADD_TO_CART": ["add", "buy", "get", "purchase", "i want", "i need"],
            "REMOVE_FROM_CART": ["remove", "delete", "take off"],
            "SEARCH_PRODUCT": ["find", "search", "show me", "do you have"],
            "CONFIRM_ORDER": ["confirm", "checkout", "pay", "ready to pay", "confirm order"],
            "CLEAR_CART": ["clear cart", "empty cart", "reset order", "start over"],
        }
        self.stop_words = ["a", "an", "the", "for", "me", "item", "product"]

    def _normalize_message(self, message: str) -> str:
        message = message.lower()
        message = re.sub(r"[^\w\s]", "", message)
        return message

    def _classify_intent(self, normalized_message: str) -> Tuple[str, str]:
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if normalized_message.startswith(keyword + " "):
                    cleaned_message = normalized_message[len(keyword) :].strip()
                    return intent, cleaned_message
                elif normalized_message == keyword:
                     return intent, ""
        return "SEARCH_PRODUCT", normalized_message

    def _get_query_embedding(self, query: str) -> List[float]:
        vector = self.embedding_model.encode(query, convert_to_numpy=True)
        return vector.tolist()

    async def _search_opensearch(self, query: str) -> List[Tuple[str, float]]:
        opensearch_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["name^3", "description", "tags^2", "category"],
                }
            },
            "size": 20,
        }
        response = await self.opensearch_client.search(
            index="airdeliver_products", body=opensearch_query
        )
        return [
            (hit["_id"], hit["_score"]) for hit in response["hits"]["hits"]
        ]

    async def _search_milvus(self, vector: List[float]) -> List[Tuple[str, float]]:
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.milvus_client.search(
            collection_name=self.milvus_collection,
            data=[vector],
            limit=20,
            search_params=search_params,
        )
        return [
            (hit.id, hit.distance) for hit in results[0]
        ]

    async def find_products_from_message(
        self, db: AsyncSession, message: str, user_id: int
    ) -> Tuple[List[Product], Dict[str, Any]]:
        normalized_message = self._normalize_message(message)
        intent, cleaned_message = self._classify_intent(normalized_message)

        if intent not in ["ADD_TO_CART", "SEARCH_PRODUCT"]:
            return [], {"intent": intent}

        if not cleaned_message:
            return [], {"intent": intent}

        query_vector = self._get_query_embedding(cleaned_message)

        opensearch_results, milvus_results = await asyncio.gather(
            self._search_opensearch(cleaned_message),
            self._search_milvus(query_vector)
        )

        all_results = opensearch_results + milvus_results
        reranked_scores = self.reranker.rerank(all_results)

        sorted_ids = sorted(
            reranked_scores, key=reranked_scores.get, reverse=True
        )[:5]

        if not sorted_ids:
            return [], {"intent": intent}

        product_ids_int = [int(pid) for pid in sorted_ids]

        statement = select(Product).where(Product.id.in_(product_ids_int))
        products = (await db.exec(statement)).all()

        product_map = {str(p.id): p for p in products}
        sorted_products = [product_map[pid] for pid in sorted_ids if pid in product_map]

        return sorted_products, {"intent": intent, "quantity": 1}

def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

def get_milvus_client() -> MilvusClient:
    return MilvusClient(uri=MILVUS_DB_PATH)

async def get_opensearch_client(
    settings: CoreSettings = Depends(get_core_settings),
) -> AsyncGenerator[AsyncOpenSearch, None]:

    hosts = [{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}]
    auth = None

    if settings.APP_ENV == "production":
        auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASS)

    client = AsyncOpenSearch(
        hosts=hosts,
        http_auth=auth,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )
    yield client
    await client.close()

def get_ai_commerce_engine(
    opensearch_client: AsyncOpenSearch = Depends(get_opensearch_client),
    milvus_client: MilvusClient = Depends(get_milvus_client),
    embedding_model: SentenceTransformer = Depends(get_embedding_model),
) -> AICommerceEngine:
    return AICommerceEngine(
        opensearch_client=opensearch_client,
        milvus_client=milvus_client,
        embedding_model=embedding_model,
    )
