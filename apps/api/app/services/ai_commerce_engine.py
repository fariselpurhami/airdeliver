# apps/api/app/services/ai_commerce_engine.py

from __future__ import annotations

from app.core.ai_profile import get_ai_profile
from app.services.ai_adapters import LocalRetrievalAdapter
from app.services.complement_evidence import catalog_asserts_complement
from app.services.catalog_visibility import is_catalog_hidden,real_catalog_predicates
from app.core.catalog_contract import PRODUCT_TEXT_MODEL_NAME, PRODUCT_TEXT_MODEL_DIMENSION, PRODUCT_TEXT_COLLECTION, DEFAULT_PRODUCT_TEXT_MODEL_REVISION, PRODUCT_SEARCH_INDEX, PRODUCT_INTENT_COLLECTION, PRODUCT_MEMORY_COLLECTION, PRODUCT_QUERY_PROMPT, PRODUCT_TEXT_PROFILE

import asyncio
import numpy as np
import base64
import hashlib
import json
import logging
import math
import os
import random
import re
import threading
import weakref
import time
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import Any, AsyncGenerator, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple, Union, cast

import torch
import torch.nn.functional as F
from fastapi import Depends
from opensearchpy import AsyncOpenSearch
from PIL import Image, UnidentifiedImageError
from pymilvus import DataType, MilvusClient
from sentence_transformers import SentenceTransformer
from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession
from transformers import AutoModel, AutoProcessor

from app.core.config import CoreSettings, get_core_settings
from app.models.product import Product
from app.services.cache_service import IAsyncCacheClient, get_cache_client

from app.services.embedding_warmup import (warm_text_encoder, WarmupPolicy, TextEmbeddingWarmupError, STARTUP_MODEL_BUDGET_SECONDS)

logger = logging.getLogger("airdeliver.engine")



@dataclass(frozen=True)
class MilvusRetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 8.0
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.2
    connect_timeout_seconds: float = 30.0

class AICommerceError(Exception):
    pass


class ConfigurationError(AICommerceError):
    pass


class BootstrapError(AICommerceError):
    pass


class ValidationError(AICommerceError):
    pass


class ExternalDependencyError(AICommerceError):
    pass


class SpendingTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    dimension: int


@dataclass(frozen=True)
class SearchFilter:
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    category: Optional[str] = None
    excluded_ids: Optional[List[int]] = None

    @classmethod
    def from_mapping(cls, value: Optional[Mapping[str, Any]]) -> "SearchFilter":
        if value is None:
            return cls()
        price_min = cls._optional_float(value.get("price_min"))
        price_max = cls._optional_float(value.get("price_max"))
        category = cls._optional_str(value.get("category"))
        
        excluded_ids = value.get("excluded_ids")
        if excluded_ids is not None:
            if not isinstance(excluded_ids, list):
                raise ValidationError("excluded_ids must be a list of positive integers")
            normalized_ids = []
            for item in excluded_ids:
                if isinstance(item, bool) or not re.fullmatch(r"[0-9]+", str(item)):
                    raise ValidationError("excluded_ids must contain positive integers")
                item_id = int(item)
                if item_id <= 0 or item_id > 9223372036854775807:
                    raise ValidationError("excluded product ID out of range")
                normalized_ids.append(item_id)
            excluded_ids = list(dict.fromkeys(normalized_ids))
        if price_min is not None and price_min < 0:
            raise ValidationError("price_min must be >= 0")
        if price_max is not None and price_max < 0:
            raise ValidationError("price_max must be >= 0")
        if price_min is not None and price_max is not None and price_min > price_max:
            raise ValidationError("price_min cannot be greater than price_max")

        return cls(price_min=price_min, price_max=price_max, category=category, excluded_ids=excluded_ids)

    @staticmethod
    def _optional_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise ValidationError("boolean is not a valid numeric filter")
        try:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("numeric filters must be finite")
            return number
        except (TypeError, ValueError) as exc:
            raise ValidationError("invalid numeric filter") from exc

    @staticmethod
    def _optional_str(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > 128:
            raise ValidationError("category filter too long")
        return text

    def to_cache_dict(self) -> Dict[str, Any]:
        return {
            "price_min": self.price_min,
            "price_max": self.price_max,
            "category": self.category,
            "excluded_ids": self.excluded_ids,
        }


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    dim: int
    description: str


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    score: float


@dataclass(frozen=True)
class EngineLimits:
    max_query_length: int = 512
    max_bundle_size: int = 4
    max_search_limit: int = 100
    max_image_search_limit: int = 50
    max_image_encoded_chars: int = 7_000_256
    max_image_bytes: int = 5 * 1024 * 1024
    max_image_pixels: int = 25_000_000
    max_image_edge: int = 16_384
    max_homepage_candidates: int = 60
    max_memory_fact_length: int = 2048
    max_category_length: int = 128
    cache_ttl_search_seconds: int = 3600
    cache_ttl_bundle_seconds: int = 86400
    # User-facing timeouts must stay well under the gunicorn worker timeout
    # (120s) so slow dependencies surface a clean ExternalDependencyError
    # instead of the worker being SIGKILLed mid-request. Models are warmed
    # at bootstrap, so 25s is generous for warm inference.
    embedding_timeout_seconds: float = 25.0
    vector_search_timeout_seconds: float = 25.0
    bundle_timeout_seconds: float = 25.0
    db_fetch_timeout_seconds: float = 25.0
    bootstrap_timeout_seconds: float = 190.0
    opensearch_timeout_seconds: float = 30.0
    memory_similarity_threshold: float = 0.70


class ProductLike(Protocol):
    id: Any
    name: str
    description: Optional[str]
    price: Optional[float]
    image_url: Optional[str]
    category: Optional[str]
    rating: Optional[float]


ACCESSORY_SAFE_KEYWORDS: frozenset[str] = frozenset(
    {
        "case", "cover", "skin", "bumper", "screen", "protector", "glass", "film",
        "charger", "adapter", "cable", "cord", "wire", "plug", "brick", "dock",
        "stand", "mount", "holder", "grip", "ring", "pop", "socket", "sleeve",
        "stylus", "pen", "pencil", "tip", "nibs", "sim", "ejector", "dongle", "hub",
        "mouse", "keyboard", "keypad", "trackpad", "monitor", "display", "webcam",
        "mic", "microphone", "speaker", "headset", "headphones", "earbuds", "pods",
        "drive", "storage", "disk", "ssd", "hdd", "card", "memory", "ram", "stick",
        "cooler", "fan", "pad", "paste", "thermal", "screw", "bracket", "hinge",
        "battery", "powerbank", "inverter", "ups", "toner", "ink", "cartridge", "ribbon",
        "lens", "filter", "cap", "hood", "tripod", "monopod", "gimbal", "stabilizer",
        "flash", "light", "diffuser", "reflector", "shutter", "remote", "trigger",
        "strap", "harness", "bag", "backpack", "cleaning", "cloth", "blower", "sensor",
        "controller", "gamepad", "joystick", "wheel", "pedal", "console", "vr",
        "docking", "station", "faceplate", "thumbstick", "paddle", "chair",
        "refill", "roller", "hose", "nozzle", "attachment", "blade", "mixer", "beater",
        "whisk", "bowl", "lid", "seal", "gasket", "pod", "capsule", "beans", "ground",
        "scale", "timer", "thermometer", "bulb", "lamp", "shade", "switch", "dimmer",
        "belt", "tie", "scarf", "socks", "laces", "shoelace", "insole", "polish", "wax",
        "hanger", "hook", "organizer", "box", "jewelry", "watch", "link", "band",
        "stud", "clip", "pin", "button", "zipper", "patch", "sponge", "applicator",
        "wand", "mirror", "tweezer", "clipper", "file", "razor", "head", "foil", "comb",
        "curler", "dryer", "sample", "tester", "travel", "kit", "set", "pack",
        "mat", "liner", "freshener", "perfume", "jumper", "jack", "wrench", "tool",
        "oil", "fluid", "wiper", "fuse", "valve", "sticker", "decal",
        "accessory", "accessories", "part", "parts", "spare", "replacement",
        "extension", "expansion", "add-on", "module", "unit", "consumable", "supply",
        "supplies", "maintenance", "service", "care", "cleaner", "spray", "wipe",
    }
)

_profile = get_ai_profile()
PRODUCT_TEXT_MODEL = ModelSpec(name=_profile.text_retrieval_model, dimension=_profile.text_retrieval_dimension)
PRODUCT_VISION_MODEL = ModelSpec(name=_profile.image_retrieval_model, dimension=_profile.image_retrieval_dimension)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sanitize_query_text(value: str, max_length: int) -> str:
    sanitized = re.sub(r"[^\w\s\-]", " ", value or "", flags=re.UNICODE)
    sanitized = _normalize_whitespace(sanitized)
    if not sanitized:
        raise ValidationError("query cannot be empty after sanitization")
    return sanitized[:max_length]


def _sanitize_category(value: Optional[str], max_length: int) -> Optional[str]:
    if value is None:
        return None
    category = _normalize_whitespace(value)
    if not category:
        return None
    if len(category) > max_length:
        raise ValidationError("category too long")
    return category


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _cache_key(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _detect_torch_device() -> str:
    accelerator = os.getenv("ACCELERATOR", "").strip().lower()
    if accelerator == "cuda" and torch.cuda.is_available():
        return "cuda"
    if accelerator == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _preferred_dtype_for_device(device: str) -> torch.dtype:
    if device == "cuda":
        return torch.float16
    return torch.float32


def _escape_milvus_string_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _build_milvus_filter(filter_obj: SearchFilter) -> str:
    expressions: List[str] = []
    if filter_obj.price_min is not None:
        expressions.append(f"price >= {filter_obj.price_min}")
    if filter_obj.price_max is not None:
        expressions.append(f"price <= {filter_obj.price_max}")
    if filter_obj.category:
        escaped = _escape_milvus_string_literal(filter_obj.category)
        expressions.append(f"category == '{escaped}'")
    if filter_obj.excluded_ids:
        ids_str = ", ".join(str(i) for i in filter_obj.excluded_ids)
        expressions.append(f"id not in [{ids_str}]")
    return " && ".join(expressions)


def _safe_product_price(product: ProductLike) -> float:
    try:
        return float(product.price or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_product_rating(product: ProductLike) -> float:
    try:
        return float(product.rating or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _clean_product_name_root(name: str) -> str:
    result = re.sub(r"\b(\d+GB|\d+TB|\d+mm|5G|4G|LTE)\b", "", name, flags=re.IGNORECASE)
    result = re.sub(r"[^\w\s]", " ", result, flags=re.UNICODE)
    return _normalize_whitespace(result)


def _tokenize_lower_words(value: str) -> set[str]:
    return set(re.findall(r"\w+", value.lower(), flags=re.UNICODE))


# One admission gate per shared model across request-scoped engine instances.
# A Python thread cannot be cancelled by an asyncio deadline. The thread itself
# owns release so timed-out/cancelled callers cannot admit overlapping work.
_TEXT_MODEL_GATES = weakref.WeakKeyDictionary()
_TEXT_MODEL_GATES_LOCK = threading.Lock()
# Process-wide: request-scoped engines share the same vision model.
_VISION_NATIVE_GATE = threading.BoundedSemaphore(2)
_VECTOR_NATIVE_GATE = threading.BoundedSemaphore(8)


def _text_model_gate(model):
    with _TEXT_MODEL_GATES_LOCK:
        gate = _TEXT_MODEL_GATES.get(model)
        if gate is None:
            gate = threading.Lock()
            _TEXT_MODEL_GATES[model] = gate
        return gate


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "ModelRegistry":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._text_model = None
                    cls._instance._text_warmup_status = {"state": "not_started"}
                    cls._instance._text_startup_rejected = threading.Event()
                    cls._instance._vision_model = None
                    cls._instance._vision_processor = None
                    cls._instance._model_lock = threading.RLock()
                    cls._instance._device = _detect_torch_device()
                    cls._instance._dtype = _preferred_dtype_for_device(cls._instance._device)
        return cls._instance

    def get_text_model(self) -> SentenceTransformer:
        if self._text_model is not None:
            return self._text_model

        with self._model_lock:
            if self._text_model is not None:
                return self._text_model

            if get_core_settings().PRODUCT_TEXT_MODEL_REVISION not in (None,DEFAULT_PRODUCT_TEXT_MODEL_REVISION):
                raise ValueError('Revision override differs from the selected versioned retrieval space')
            logger.info("loading text embedding model", extra={"model": PRODUCT_TEXT_MODEL.name, "device": self._device})
            logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)

            # The model lock proves the prior native attempt has drained. A
            # new attempt gets its own rejection event; never revive old work.
            rejected = threading.Event()
            self._text_startup_rejected = rejected
            settings = get_core_settings()
            policy = WarmupPolicy(budget_seconds=settings.TEXT_WARMUP_BUDGET_SECONDS,
                                  sample_max_seconds=settings.TEXT_WARMUP_SAMPLE_MAX_SECONDS,
                                  max_attempts=max(8, int(settings.TEXT_WARMUP_BUDGET_SECONDS)))
            self._text_warmup_status = {"state": "warming_up"}
            def expire():
                rejected.set()
                self._text_warmup_status = {"state": "failed", "error": "startup_budget_exhausted"}
                logger.error("text embedding startup budget exhausted; readiness rejected")
            timer = threading.Timer(settings.TEXT_STARTUP_BUDGET_SECONDS, expire)
            timer.daemon = True
            timer.start()
            warmup_timer = None
            try:
                if PRODUCT_TEXT_PROFILE!='gte-v1' and get_core_settings().PRODUCT_TEXT_MODEL_REVISION not in (None,DEFAULT_PRODUCT_TEXT_MODEL_REVISION):
                    raise ValueError('Revision override differs from Harrier versioned space')
                factory=SentenceTransformer
                if PRODUCT_TEXT_PROFILE!='gte-v1':
                    from scripts.owner_embedding_benchmark import resolve,validate_files,definitions
                    path,_=resolve(PRODUCT_TEXT_PROFILE.split('-')[0]);validate_files(path,definitions()[PRODUCT_TEXT_PROFILE.split('-')[0]])
                    def factory(_name,**kwargs):
                        return SentenceTransformer(str(path),local_files_only=True,**kwargs)
                model = LocalRetrievalAdapter(get_ai_profile()).create_text_encoder(
                    factory,
                    revision=get_core_settings().PRODUCT_TEXT_MODEL_REVISION or DEFAULT_PRODUCT_TEXT_MODEL_REVISION,
                    trust_remote_code=False,
                    device=self._device,
                    model_kwargs={"dtype": self._dtype},
                )
                try:
                    if hasattr(model[0], "auto_model") and hasattr(model[0].auto_model, "config"):
                        model[0].auto_model.config.use_cache = False
                except Exception:
                    logger.debug("unable to disable transformer use_cache on embedding model")
                model.max_seq_length = 256 if PRODUCT_TEXT_PROFILE!='gte-v1' else 8192
                model.to(self._device)
                model.eval()
                warmup_timer = threading.Timer(policy.budget_seconds, expire)
                warmup_timer.daemon = True
                warmup_timer.start()
                with torch.no_grad():
                    report = warm_text_encoder(model, PRODUCT_TEXT_MODEL.dimension, policy=policy, rejected=rejected)
                if rejected.is_set():
                    raise TextEmbeddingWarmupError("Text model startup budget exhausted")
                self._text_warmup_status = report
                self._text_model = model
                logger.info("text embedding model ready dimension=%d", PRODUCT_TEXT_MODEL.dimension)
                return model
            except BaseException:
                self._text_warmup_status = {"state": "failed", "error": "warmup_failed"}
                logger.exception("text embedding startup failed; model not published")
                raise
            finally:
                timer.cancel()
                if warmup_timer is not None:
                    warmup_timer.cancel()

    def text_readiness(self):
        return dict(self._text_warmup_status)

    def reject_text_startup(self):
        self._text_startup_rejected.set()
        self._text_warmup_status = {"state": "failed", "error": "startup_deadline_exceeded"}

    def get_vision_stack(self) -> Tuple[Any, Any]:
        if self._vision_model is not None and self._vision_processor is not None:
            return self._vision_model, self._vision_processor

        with self._model_lock:
            if self._vision_model is not None and self._vision_processor is not None:
                return self._vision_model, self._vision_processor

            logger.info("loading vision model", extra={"model": PRODUCT_VISION_MODEL.name, "device": self._device})

            revision = get_core_settings().PRODUCT_VISION_MODEL_REVISION
            processor = LocalRetrievalAdapter(get_ai_profile()).create_image_component(AutoProcessor.from_pretrained, revision=revision)
            model = LocalRetrievalAdapter(get_ai_profile()).create_image_component(
                AutoModel.from_pretrained,
                revision=revision,
                trust_remote_code=True,
                torch_dtype=self._dtype if self._device == "cuda" else None,
            ).to(self._device)

            model.eval()

            with torch.no_grad():
                dummy = torch.randn(1, 3, 384, 384, device=self._device, dtype=self._dtype)
                model.get_image_features(pixel_values=dummy)

            self._vision_processor = processor
            self._vision_model = model

            logger.info("vision model loaded", extra={"dimension": PRODUCT_VISION_MODEL.dimension})
            return self._vision_model, self._vision_processor

    @property
    def device(self) -> str:
        return self._device

    @property
    def dtype(self) -> torch.dtype:
        return self._dtype


model_registry = ModelRegistry()


class HybridSearchReranker:
    def __init__(self, k: int = 60, epsilon: float = 1e-9) -> None:
        if k <= 0:
            raise ConfigurationError("reranker k must be > 0")
        if epsilon <= 0:
            raise ConfigurationError("reranker epsilon must be > 0")
        self._k = k
        self._epsilon = epsilon

    def _normalize_scores(self, scores: Mapping[str, float]) -> Dict[str, float]:
        if not scores:
            return {}

        values = list(scores.values())
        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum

        if span < self._epsilon:
            return {document_id: 1.0 for document_id in scores}

        return {document_id: (score - minimum) / span for document_id, score in scores.items()}

    def rerank(
        self,
        opensearch_results: Sequence[Tuple[str, float]],
        milvus_results: Sequence[Tuple[str, float]],
    ) -> Dict[str, float]:
        os_scores = {str(document_id): float(score) for document_id, score in opensearch_results}
        milvus_scores = {str(document_id): float(score) for document_id, score in milvus_results}

        normalized_os = self._normalize_scores(os_scores)
        normalized_milvus = self._normalize_scores(milvus_scores)

        merged_ids = set(normalized_os.keys()) | set(normalized_milvus.keys())
        combined: Dict[str, float] = {}

        for document_id in merged_ids:
            score_os = normalized_os.get(document_id, 0.0)
            score_milvus = normalized_milvus.get(document_id, 0.0)
            combined[document_id] = (1.0 / (self._k + (1.0 - score_os))) + (1.0 / (self._k + (1.0 - score_milvus)))

        return combined


class AICommerceEngine:
    SCHEMA_CONFIG: Dict[str, CollectionSpec] = {
        "product_text": CollectionSpec(
            name=PRODUCT_TEXT_COLLECTION,
            dim=PRODUCT_TEXT_MODEL.dimension,
            description="Semantic Product Search",
        ),
        "product_visual": CollectionSpec(
            name="airdeliver_visual_sota_v4",
            dim=PRODUCT_VISION_MODEL.dimension,
            description="Visual Similarity Search",
        ),
        "intent": CollectionSpec(
            name=PRODUCT_INTENT_COLLECTION,
            dim=PRODUCT_TEXT_MODEL.dimension,
            description="User Intent Classification",
        ),
        "memory": CollectionSpec(
            name=PRODUCT_MEMORY_COLLECTION,
            dim=PRODUCT_TEXT_MODEL.dimension,
            description="Long-term User Context",
        ),
    }

    def __init__(
        self,
        *,
        opensearch_client: AsyncOpenSearch,
        milvus_client: MilvusClient,
        embedding_model: SentenceTransformer,
        cache_client: Optional[IAsyncCacheClient] = None,
        limits: Optional[EngineLimits] = None,
    ) -> None:
        self.opensearch_client = opensearch_client
        self.milvus_client = milvus_client
        self.embedding_model = embedding_model
        self.cache_client = cache_client
        self.limits = limits or EngineLimits()
        self.reranker = HybridSearchReranker()

        self.milvus_product_text_col = self.SCHEMA_CONFIG["product_text"].name
        self.milvus_product_visual_col = self.SCHEMA_CONFIG["product_visual"].name
        self.intent_collection = self.SCHEMA_CONFIG["intent"].name
        self.user_memory_collection = self.SCHEMA_CONFIG["memory"].name

        self._bootstrap_lock = asyncio.Lock()
        self._bootstrapped = False
        self._embedding_semaphore = asyncio.Semaphore(4)
        self._vector_search_semaphore = asyncio.Semaphore(8)
        self._image_inference_semaphore = asyncio.Semaphore(2)

    async def bootstrap(self) -> None:
        if self._bootstrapped:
            return

        async with self._bootstrap_lock:
            if self._bootstrapped:
                return

            started_at = time.perf_counter()
            await asyncio.wait_for(self._ensure_all_collections(), timeout=self.limits.bootstrap_timeout_seconds)
            await self.ensure_opensearch_index()
            self._bootstrapped = True

            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.info("ai commerce engine bootstrapped", extra={"elapsed_ms": round(elapsed_ms, 2)})

    async def _ensure_all_collections(self) -> None:
        for key, spec in self.SCHEMA_CONFIG.items():
            try:
                exists = await asyncio.to_thread(self.milvus_client.has_collection, spec.name)
                if exists:
                    logger.debug("milvus collection ready", extra={"collection": spec.name})
                    continue

                logger.info("creating milvus collection", extra={"collection": spec.name, "dim": spec.dim, "kind": key})

                if key in {"product_text", "product_visual"}:
                    await asyncio.to_thread(self._create_product_collection, spec.name, spec.dim)
                elif key == "intent":
                    await asyncio.to_thread(self._create_intent_collection, spec.name, spec.dim)
                elif key == "memory":
                    await asyncio.to_thread(self._create_memory_collection, spec.name, spec.dim)
                else:
                    raise BootstrapError(f"unsupported collection type: {key}")

            except Exception as exc:
                logger.exception("milvus collection bootstrap failed", extra={"collection": spec.name, "kind": key})
                raise BootstrapError(f"failed to initialize collection {spec.name}") from exc

    def _create_product_collection(self, name: str, dim: int) -> None:
        schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field(field_name="price", datatype=DataType.FLOAT)
        schema.add_field(field_name="rating", datatype=DataType.FLOAT)
        schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=128)

        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        index_params.add_index(field_name="price", index_type="STL_SORT")
        index_params.add_index(field_name="rating", index_type="STL_SORT")

        self.milvus_client.create_collection(
            collection_name=name,
            schema=schema,
            index_params=index_params,
            consistency_level="Bounded",
        )

    def _create_intent_collection(self, name: str, dim: int) -> None:
        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field(field_name="intent_label", datatype=DataType.VARCHAR, max_length=64)

        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")

        self.milvus_client.create_collection(collection_name=name, schema=schema, index_params=index_params)
        self._hydrate_intents(name)

    def _create_memory_collection(self, name: str, dim: int) -> None:
        schema = MilvusClient.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field(field_name="user_id", datatype=DataType.INT64)
        schema.add_field(field_name="fact_text", datatype=DataType.VARCHAR, max_length=self.limits.max_memory_fact_length)
        schema.add_field(field_name="timestamp", datatype=DataType.INT64)

        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 8, "efConstruction": 100},
        )
        index_params.add_index(field_name="user_id", index_type="STL_SORT")
        index_params.add_index(field_name="timestamp", index_type="STL_SORT")

        self.milvus_client.create_collection(collection_name=name, schema=schema, index_params=index_params)

    def _hydrate_intents(self, collection_name: str) -> None:
        try:
            existing = self.milvus_client.query(
                collection_name,
                filter="id >= 0",
                output_fields=["id"],
                limit=1,
            )
            if existing:
                return
        except Exception:
            logger.debug("intent hydration existence check failed; continuing with insert attempt")

        intent_map: Dict[str, List[str]] = {
            "ADD_TO_CART": [
                "add to cart", "buy now", "purchase this", "put in bag",
                "ضيف للسلة", "اشتري ده", "محتاج المنتج ده", "حطه في العربة", "شراء",
            ],
            "CONFIRM_ORDER": [
                "checkout", "confirm order", "pay now", "finalize my manifest",
                "تأكيد الطلب", "دفع", "خلص الشروة", "إتمام الشراء", "شحن",
            ],
            "CLEAR_CART": [
                "empty my cart", "clear manifest", "remove everything",
                "مسح السلة", "فضي الكارت", "شيل كل حاجة",
            ],
        }

        rows: List[Dict[str, Any]] = []
        for label, phrases in intent_map.items():
            vectors = self.embedding_model.encode(phrases, convert_to_numpy=True, **({"prompt":PRODUCT_QUERY_PROMPT,"normalize_embeddings":True} if PRODUCT_TEXT_PROFILE!='gte-v1' else {}))
            for vector in vectors:
                rows.append({"vector": vector, "intent_label": label})

        if rows:
            self.milvus_client.insert(collection_name=collection_name, data=rows)

    async def get_query_embedding(self, query: str) -> List[float]:
        """Public embedding contract used by NLU's confidence assessment."""
        return await self._get_query_embedding(query)

    async def _get_query_embedding(self, query: str) -> List[float]:
        sanitized = _sanitize_query_text(query, self.limits.max_query_length)
        from app.services.query_vector_cache import QueryVectorCache
        if not hasattr(self,'_query_vectors'):self._query_vectors=QueryVectorCache()
        vector_key=(id(self.embedding_model),PRODUCT_TEXT_MODEL_NAME,DEFAULT_PRODUCT_TEXT_MODEL_REVISION,PRODUCT_QUERY_PROMPT,PRODUCT_TEXT_MODEL.dimension,sanitized)
        cached=self._query_vectors.get(vector_key)
        if cached is not None:return cached

        gate = _text_model_gate(self.embedding_model)
        started = time.monotonic()
        deadline = started + self.limits.embedding_timeout_seconds
        acquired = False
        submitted = False
        service_started = None
        try:
            while not acquired:
                acquired = gate.acquire(blocking=False)
                if acquired:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                await asyncio.sleep(min(.01, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            service_started = time.monotonic()

            def encode_and_release():
                try:
                    cached=self._query_vectors.get(vector_key)
                    if cached is not None:return np.asarray(cached)
                    result=self.embedding_model.encode(sanitized, convert_to_numpy=True, **({"prompt":PRODUCT_QUERY_PROMPT,"normalize_embeddings":True} if PRODUCT_TEXT_PROFILE!='gte-v1' else {}))
                    self._query_vectors.put(vector_key,result.tolist(),PRODUCT_TEXT_MODEL.dimension)
                    return result
                finally:
                    gate.release()
                    logger.info("text embedding service finished: service_seconds=%.4f query_characters=%d", time.monotonic()-service_started, len(sanitized), extra={
                        "service_seconds": round(time.monotonic()-service_started, 4),
                        "query_characters": len(sanitized),
                    })

            future = asyncio.get_running_loop().run_in_executor(None, encode_and_release)
            submitted = True
            # Consume late exceptions after timeout without leaking raw inputs or
            # producing an unobserved-future exception. Active compute still owns gate.
            def consume_done(done):
                if not done.cancelled():
                    done.exception()
            future.add_done_callback(consume_done)
            vector = await asyncio.wait_for(asyncio.shield(future), timeout=remaining)
        except asyncio.TimeoutError as exc:
            logger.warning("text embedding deadline exceeded: elapsed_seconds=%.4f deadline_seconds=%.4f compute_submitted=%s", time.monotonic()-started, self.limits.embedding_timeout_seconds, submitted, extra={
                "elapsed_seconds": round(time.monotonic()-started, 4),
                "deadline_seconds": self.limits.embedding_timeout_seconds,
                "compute_submitted": submitted,
                "query_characters": len(sanitized),
            })
            raise ExternalDependencyError("embedding generation timed out") from exc
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise ExternalDependencyError("embedding generation failed") from exc
        finally:
            if acquired and not submitted:
                gate.release()

        vector_list = vector.tolist()
        if len(vector_list) != PRODUCT_TEXT_MODEL.dimension:
            raise ExternalDependencyError(
                f"unexpected embedding dimension {len(vector_list)} != {PRODUCT_TEXT_MODEL.dimension}"
            )
        return cast(List[float], vector_list)

    async def generate_perfect_bundle(self, db: AsyncSession, anchor: Product) -> List[Product]:
        await self.bootstrap()

        if anchor is None or getattr(anchor, "id", None) is None:
            raise ValidationError("anchor product is required")

        # The caller/cache/index can hold old catalog facts. Resolve the anchor
        # and all displayed recommendations from the current database rows.
        anchor_rows = await self._fetch_products_from_db_by_ids(db, [int(anchor.id)])
        if not anchor_rows or not anchor_rows[0].is_active:
            return []
        anchor = anchor_rows[0]
        anchor_price = _safe_product_price(anchor)
        max_accessory_ratio = 2.0 if anchor_price < 50 else 0.6
        max_price = anchor_price * max_accessory_ratio if anchor_price > 0 else 1000.0
        search_filter = SearchFilter(price_max=max_price, excluded_ids=[int(anchor.id)])
        cache_key = _cache_key("bundle", {"anchor_id": str(anchor.id), "version": 9})

        if self.cache_client:
            try:
                cached = await self.cache_client.get_json(cache_key)
                if isinstance(cached, list) and cached:
                    # Read existing snapshot caches as IDs only. New writes use
                    # IDs too, so mutable prices/names never become authority.
                    ids = []
                    for item in cached[:self.limits.max_bundle_size]:
                        raw = item.get("id") if isinstance(item, dict) else item
                        if type(raw) is int and 0 < raw <= 9223372036854775807:
                            ids.append(raw)
                    rows = await self._fetch_products_from_db_by_ids(db, ids)
                    current_cached = [p for p in self._filter_products(rows, search_filter)
                                      if catalog_asserts_complement(anchor, p)][:self.limits.max_bundle_size]
                    if current_cached:
                        return current_cached
            except Exception:
                logger.warning("bundle cache read failed", extra={"anchor_id": str(anchor.id)})

        started_at = time.perf_counter()
        try:
            clean_name_root = _clean_product_name_root(anchor.name)
            anchor_category = _safe_str(getattr(anchor, "category", ""), "").lower()
            search_queries = [
                f"accessories for {clean_name_root}",
                f"compatible parts {clean_name_root}",
                f"essential gear {clean_name_root}",
            ]

            # An AsyncSession owns mutable transaction state and cannot be
            # shared by simultaneous database operations. Keep the three
            # searches inside one deadline, but use the session serially.
            try:
                async with asyncio.timeout(self.limits.bundle_timeout_seconds):
                    grouped_results = []
                    for query in search_queries:
                        grouped_results.append(await self.perform_hybrid_search_pure(
                            db, query, limit=5, filters=search_filter.to_cache_dict()
                        ))
            except asyncio.TimeoutError:
                logger.warning("bundle generation timed out", extra={"anchor_id": str(anchor.id)})
                fallback = await self._get_emergency_fallback(db, anchor_category or clean_name_root, search_filter)
                current_fallback = await self._fetch_products_from_db_by_ids(db, [int(p.id) for p in fallback])
                return [p for p in self._filter_products(current_fallback, search_filter)
                        if catalog_asserts_complement(anchor, p)][:self.limits.max_bundle_size]

            approved: List[Product] = []
            seen_ids: set[Any] = {anchor.id}
            seen_utilities: set[str] = set()

            for group in grouped_results:
                selected: Optional[Product] = None
                for item in group:
                    if item.id in seen_ids or not catalog_asserts_complement(anchor, item):
                        continue

                    item_price = _safe_product_price(item)
                    item_name_lower = item.name.lower()
                    item_tokens = _tokenize_lower_words(item_name_lower)
                    is_safe_accessory = not item_tokens.isdisjoint(ACCESSORY_SAFE_KEYWORDS)
                    has_anchor_name = clean_name_root.lower() in item_name_lower

                    if has_anchor_name and not is_safe_accessory and anchor_price > 0 and item_price > anchor_price * 0.4:
                        continue

                    item_category = _safe_str(getattr(item, "category", ""), "").lower()
                    if item_category and item_category == anchor_category:
                        if not is_safe_accessory and anchor_price > 0 and item_price > anchor_price * 0.2:
                            continue

                    found_utilities = item_tokens.intersection(ACCESSORY_SAFE_KEYWORDS)
                    utility_fingerprint = "-".join(sorted(found_utilities)) if found_utilities else "unknown_wildcard"

                    if utility_fingerprint in seen_utilities:
                        continue

                    selected = item
                    seen_ids.add(item.id)
                    seen_utilities.add(utility_fingerprint)
                    break

                if selected is not None:
                    approved.append(selected)

            if len(approved) < 2:
                fallback_items = await self._get_emergency_fallback(db, clean_name_root, search_filter)
                for item in fallback_items:
                    if item.id in seen_ids or not catalog_asserts_complement(anchor, item):
                        continue
                    approved.append(item)
                    seen_ids.add(item.id)
                    if len(approved) >= self.limits.max_bundle_size:
                        break

            current = await self._fetch_products_from_db_by_ids(db, [int(p.id) for p in approved])
            final_result = [p for p in self._filter_products(current, search_filter)
                            if catalog_asserts_complement(anchor, p)][:self.limits.max_bundle_size]

            if self.cache_client and final_result:
                try:
                    await self.cache_client.set_json(
                        cache_key,
                        [int(item.id) for item in final_result],
                        ttl=self.limits.cache_ttl_bundle_seconds,
                    )
                except Exception:
                    logger.warning("bundle cache write failed", extra={"anchor_id": str(anchor.id)})

            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "bundle generated",
                extra={"anchor_id": str(anchor.id), "count": len(final_result), "elapsed_ms": round(elapsed_ms, 2)},
            )
            return final_result

        except Exception:
            logger.exception("bundle generation failed", extra={"anchor_id": str(getattr(anchor, "id", "unknown"))})
            return []

    async def _get_emergency_fallback(
        self,
        db: AsyncSession,
        keyword: str,
        filters: Union[SearchFilter, Mapping[str, Any], None],
    ) -> List[Product]:
        filter_obj = filters if isinstance(filters, SearchFilter) else SearchFilter.from_mapping(filters)
        query = f"best rated accessories for {keyword}"
        return await self.perform_hybrid_search_pure(db, query, limit=6, filters=filter_obj.to_cache_dict())

    async def get_fresh_homepage_matrix(
        self,
        db: AsyncSession,
        user_id: int,
        seen_ids: List[int],
        spending_tier: str = "MEDIUM",
    ) -> List[Product]:
        await self.bootstrap()

        try:
            tier = SpendingTier(spending_tier.upper())
        except ValueError:
            tier = SpendingTier.MEDIUM

        try:
            universal_contexts = [
                "trending items",
                "new arrivals",
                "top rated collection",
                "most popular",
                "editors choice",
                "essential picks",
                "best selling",
                "featured products",
            ]

            if tier == SpendingTier.HIGH:
                price_adjectives = "premium luxury exclusive high-end"
            elif tier == SpendingTier.LOW:
                price_adjectives = "affordable budget value deal"
            else:
                price_adjectives = "best value quality"

            seed_material = f"{user_id}:{tier.value}:{len(seen_ids)}"
            deterministic_random = random.Random(hashlib.sha256(seed_material.encode("utf-8")).hexdigest())
            seed = deterministic_random.choice(universal_contexts)
            target_query = f"{price_adjectives} {seed}"

            candidates = await self.perform_hybrid_search_pure(
                db,
                target_query,
                limit=min(self.limits.max_homepage_candidates, 60),
                filters={},
            )

            if not candidates:
                statement = select(Product).where(col(Product.id).notin_(seen_ids))
                if tier == SpendingTier.HIGH:
                    statement = statement.order_by(col(Product.price).desc())
                elif tier == SpendingTier.LOW:
                    statement = statement.order_by(col(Product.price).asc())
                else:
                    statement = statement.order_by(col(Product.rating).desc())

                candidates = list((await db.execute(statement.limit(20))).scalars().all())

            fresh_products: List[Product] = []
            for product in candidates:
                if product.id not in seen_ids:
                    fresh_products.append(product)
                    if len(fresh_products) >= 8:
                        break

            if not fresh_products:
                fresh_products = list(candidates[:8])

            deterministic_random.shuffle(fresh_products)
            return fresh_products

        except Exception:
            logger.exception("homepage matrix generation failed", extra={"user_id": user_id, "tier": tier.value})
            return []

    async def find_genius_alternatives(self, db: AsyncSession, removed_id: int, limit: int = 3) -> List[Product]:
        await self.bootstrap()

        if removed_id <= 0:
            raise ValidationError("removed_id must be > 0")
        if limit <= 0:
            raise ValidationError("limit must be > 0")

        try:
            removed_item = await db.get(Product, removed_id)
            if not removed_item:
                return []

            anchor_price = _safe_product_price(removed_item)
            price_min = anchor_price * 0.7 if anchor_price > 50 else 0.0
            price_max = anchor_price * 1.3 if anchor_price > 0 else 1_000_000.0
            category = _sanitize_category(removed_item.category, self.limits.max_category_length)

            alternative_filter = SearchFilter(price_min=price_min, price_max=price_max, category=category, excluded_ids=[int(removed_id)])
            alternatives: List[Product] = []

            try:
                filter_expr_parts = [
                    f"id != {int(removed_id)}",
                    f"price >= {price_min}",
                    f"price <= {price_max}",
                ]
                if category:
                    filter_expr_parts.append(f"category == '{_escape_milvus_string_literal(category)}'")
                filter_expr = " && ".join(filter_expr_parts)

                record = await asyncio.to_thread(
                    self.milvus_client.query,
                    self.milvus_product_text_col,
                    filter=f"id == {int(removed_id)}",
                    output_fields=["vector"],
                    limit=1,
                )

                if record:
                    vector = record[0]["vector"]
                    search_res = await asyncio.to_thread(
                        self.milvus_client.search,
                        self.milvus_product_text_col,
                        data=[vector],
                        filter=filter_expr,
                        limit=limit,
                        output_fields=["id"],
                        search_params={"metric_type": "COSINE", "params": {"ef": 64}},
                    )
                    if search_res and search_res[0]:
                        ids = [int(hit["entity"]["id"]) for hit in search_res[0]]
                        alternatives = self._filter_products(
                            await self._fetch_products_from_db_by_ids(db, ids), alternative_filter)
            except Exception:
                logger.warning("vector alternative search failed", extra={"removed_id": removed_id}, exc_info=True)

            if not alternatives:
                query = f"best quality alternative to {removed_item.name} {removed_item.category or ''}"
                filters = alternative_filter.to_cache_dict()
                alternatives = await self.perform_hybrid_search_pure(db, query, limit=limit, filters=filters)
                alternatives = self._filter_products(alternatives, alternative_filter)

            if not alternatives:
                statement = (
                    select(Product)
                    .where(
                        Product.category == removed_item.category,
                        Product.is_active.is_(True),*real_catalog_predicates(Product),
                        Product.id != removed_id,
                        Product.price >= price_min,
                        Product.price <= price_max,
                    )
                    .order_by(col(Product.rating).desc())
                    .limit(limit)
                )
                alternatives = list((await db.execute(statement)).scalars().all())

            return self._filter_products(alternatives, alternative_filter)[:limit]

        except Exception:
            logger.exception("alternative discovery failed", extra={"removed_id": removed_id, "limit": limit})
            return []

    async def perform_hybrid_search_pure(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 50,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Product]:
        await self.bootstrap()

        if limit <= 0:
            return []
        safe_limit = min(limit, self.limits.max_search_limit)
        filter_obj = SearchFilter.from_mapping(filters)
        sanitized_query = _sanitize_query_text(query, self.limits.max_query_length)

        cache_key = _cache_key(
            "search",
            {
                "query": sanitized_query,
                "limit": safe_limit,
                "filters": filter_obj.to_cache_dict(),
                "version": 4, "retrieval_model":PRODUCT_TEXT_MODEL_NAME,
                "revision":DEFAULT_PRODUCT_TEXT_MODEL_REVISION,"dimension":PRODUCT_TEXT_MODEL.dimension,"prompt":PRODUCT_QUERY_PROMPT,
            },
        )

        if self.cache_client:
            try:
                cached_ids = await self.cache_client.get_json(cache_key)
                if cached_ids and isinstance(cached_ids, list):
                    products = await self._fetch_products_from_db_by_ids(db, [int(item) for item in cached_ids])
                    return self._filter_products(products, filter_obj)[:safe_limit]
            except Exception:
                logger.warning("search cache read failed", extra={"query": sanitized_query})

        async def semantic_search():
            try:
                async with asyncio.timeout(get_core_settings().SEARCH_EMBEDDING_BUDGET_SECONDS):
                    query_vector=await self._get_query_embedding(sanitized_query)
                    return await self._search_milvus_text(query_vector,safe_limit,filter_obj)
            except asyncio.CancelledError:raise
            except Exception as exc:
                logger.warning('semantic_enrichment_withheld error_type=%s',type(exc).__name__)
                return []

        # Keyword work no longer waits for semantic encode; both are bounded.
        opensearch_task=self._search_opensearch(sanitized_query,safe_limit,filter_obj)
        milvus_task=semantic_search()

        async def observed(stage, operation):
            started = time.monotonic()
            logger.info("hybrid_stage_started stage=%s", stage)
            try:
                result = await operation
            except BaseException as exc:
                logger.warning("hybrid_stage_failed stage=%s error_type=%s", stage, type(exc).__name__)
                raise
            logger.info("hybrid_stage_completed stage=%s elapsed_ms=%s", stage, round((time.monotonic()-started)*1000))
            return result

        opensearch_results, milvus_results = await asyncio.gather(
            observed("opensearch", opensearch_task),
            observed("milvus", milvus_task),
            return_exceptions=True,
        )

        os_res = opensearch_results if not isinstance(opensearch_results, Exception) else []
        mil_res = milvus_results if not isinstance(milvus_results, Exception) else []

        reranked_scores = self.reranker.rerank(
            [(result.document_id, result.score) for result in cast(Sequence[SearchResult], os_res)],
            [(result.document_id, result.score) for result in cast(Sequence[SearchResult], mil_res)],
        )

        logger.info("hybrid_reranking_completed", extra={"candidate_count": len(reranked_scores)})
        sorted_ids = sorted(reranked_scores.keys(), key=lambda document_id: reranked_scores[document_id], reverse=True)[:safe_limit]

        if not sorted_ids:
            logger.info("hybrid search returned no vector/keyword results; using sql fallback", extra={"query": sanitized_query})
            return await self._fallback_sql_search(db, sanitized_query, safe_limit, filter_obj)

        try:
            products = await self._fetch_products_from_db_by_ids(db, [int(document_id) for document_id in sorted_ids])

            products = self._filter_products(products, filter_obj)
            if self.cache_client and products:
                try:
                    await self.cache_client.set_json(
                        cache_key,
                        [int(product.id) for product in products],
                        ttl=self.limits.cache_ttl_search_seconds,
                    )
                except Exception:
                    logger.warning("search cache write failed", extra={"query": sanitized_query})

            return products

        except Exception:
            logger.exception("failed to fetch ranked products from database", extra={"query": sanitized_query})
            return await self._fallback_sql_search(db, sanitized_query, safe_limit, filter_obj)

    async def _search_opensearch(
        self,
        query: str,
        limit: int,
        filters: SearchFilter,
    ) -> List[SearchResult]:
        must_clauses: List[Dict[str, Any]] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["name^5", "tags^3", "description"],
                    "fuzziness": "AUTO",
                    "type": "best_fields",
                }
            }
        ]
        must_not_clauses: List[Dict[str, Any]] = []
        if filters.price_min is not None:
            must_clauses.append({"range": {"price": {"gte": filters.price_min}}})
        if filters.price_max is not None:
            must_clauses.append({"range": {"price": {"lte": filters.price_max}}})
        if filters.category:
            must_clauses.append({"term": {"category": filters.category}})
        
        if filters.excluded_ids:
            must_not_clauses.append({"terms": {"_id": [str(i) for i in filters.excluded_ids]}})

        try:
            response = await asyncio.wait_for(
                self.opensearch_client.search(
                    index=PRODUCT_SEARCH_INDEX,
                    body={
                        "query": {"bool": {"must": must_clauses, "must_not": must_not_clauses}},
                        "size": limit,
                        "_source": False,
                    },
                    request_timeout=self.limits.opensearch_timeout_seconds,
                ),
                timeout=self.limits.opensearch_timeout_seconds,
            )
            hits = response.get("hits", {}).get("hits", [])
            return [
                SearchResult(document_id=str(hit["_id"]), score=float(hit.get("_score", 0.0)))
                for hit in hits
                if "_id" in hit
            ]
        except Exception as exc:
            logger.warning("opensearch search failed", extra={"query": query, "limit": limit}, exc_info=True)
            if isinstance(exc, asyncio.CancelledError):
                raise
            return []

    async def _search_milvus_text(
        self,
        vector: Sequence[float],
        limit: int,
        filters: SearchFilter,
    ) -> List[SearchResult]:
        if not vector:
            return []

        if len(vector) != PRODUCT_TEXT_MODEL.dimension:
            logger.error(
                "text vector dimension mismatch",
                extra={"expected": PRODUCT_TEXT_MODEL.dimension, "actual": len(vector)},
            )
            return []

        filter_str = _build_milvus_filter(filters)

        async with asyncio.timeout(self.limits.vector_search_timeout_seconds):
            async with self._vector_search_semaphore:
                return await self._search_milvus_text_acquired(vector, limit, filter_str)

    async def _run_vector_native(self, function, **kwargs):
        """Bound shared native search, including work surviving caller cancellation."""
        deadline = time.monotonic() + self.limits.vector_search_timeout_seconds
        acquired = submitted = False
        try:
            while not acquired:
                acquired = _VECTOR_NATIVE_GATE.acquire(blocking=False)
                if acquired:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                await asyncio.sleep(min(.01, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            def call_and_release():
                try:
                    return function(timeout=remaining, **kwargs)
                finally:
                    _VECTOR_NATIVE_GATE.release()
            future = asyncio.get_running_loop().run_in_executor(None, call_and_release)
            submitted = True
            future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            return await asyncio.wait_for(asyncio.shield(future), timeout=remaining)
        finally:
            if acquired and not submitted:
                _VECTOR_NATIVE_GATE.release()

    async def _search_milvus_text_acquired(self, vector, limit, filter_str):
        try:
            response = await self._run_vector_native(
                self.milvus_client.search,
                collection_name=self.milvus_product_text_col,
                data=[list(vector)], limit=limit, filter=filter_str,
                output_fields=["id"],
                search_params={"metric_type": "COSINE", "params": {"ef": 64}},
            )
        except Exception:
            logger.warning("milvus text search failed", extra={"limit": limit, "filter": filter_str}, exc_info=True)
            return []

        if not response or not response[0]:
            return []

        return [
            SearchResult(document_id=str(hit["entity"]["id"]), score=float(hit["distance"]))
            for hit in response[0]
            if hit.get("entity") and "id" in hit["entity"]
        ]

    async def search_by_image_vector(self, image_input: Union[str, List[float]], limit: int = 8) -> List[Product]:
        await self.bootstrap()

        if limit <= 0:
            return []
        safe_limit = min(limit, self.limits.max_image_search_limit)

        try:
            if isinstance(image_input, list):
                vector = [float(value) for value in image_input]
            elif isinstance(image_input, str):
                vector = await self._encode_image_to_vector(image_input)
            else:
                raise ValidationError("image_input must be base64 string or list[float]")

            if len(vector) != PRODUCT_VISION_MODEL.dimension:
                raise ValidationError(
                    f"image vector dimension mismatch: expected {PRODUCT_VISION_MODEL.dimension}, got {len(vector)}"
                )

            async with self._vector_search_semaphore:
                results = await self._run_vector_native(
                    self.milvus_client.search,
                    collection_name=self.milvus_product_visual_col,
                    data=[vector], limit=safe_limit * 2, output_fields=["id"],
                    search_params={"metric_type": "COSINE", "params": {"ef": 100}},
                )

            if not results or not results[0]:
                return []

            ids = [int(hit["entity"]["id"]) for hit in results[0] if hit.get("entity") and "id" in hit["entity"]]
            return await self._fetch_products_by_ids(ids)

        except Exception:
            logger.exception("visual search failed", extra={"limit": safe_limit})
            return []

    def _decode_image_bounded(self, image_input: str) -> Image.Image:
        """Check compressed and expanded size before RGB allocation/model work."""
        if not isinstance(image_input, str) or len(image_input) > self.limits.max_image_encoded_chars:
            raise ValidationError("image input exceeds encoded size limit")
        encoded = image_input.split("base64,", 1)[1] if "base64," in image_input else image_input
        if len(encoded) > 4 * ((self.limits.max_image_bytes + 2) // 3):
            raise ValidationError("image input exceeds byte limit")
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValidationError("invalid base64 image input") from exc
        if not image_bytes or len(image_bytes) > self.limits.max_image_bytes:
            raise ValidationError("image input exceeds byte limit")
        try:
            with Image.open(BytesIO(image_bytes)) as source:
                width, height = source.size
                if (width <= 0 or height <= 0 or max(width, height) > self.limits.max_image_edge
                        or width * height > self.limits.max_image_pixels):
                    raise ValidationError("image input exceeds pixel limit")
                # Preserve existing first-frame RGB behavior, but fully load while
                # the source is open and only after checking dimensions.
                source.load()
                return source.convert("RGB")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValidationError("invalid or oversized image payload") from exc

    async def _encode_image_to_vector(self, image_input: str) -> List[float]:
        """Native decode/inference owns admission until the worker really ends."""
        deadline = time.monotonic() + self.limits.vector_search_timeout_seconds
        acquired = submitted = False
        try:
            while not acquired:
                acquired = _VISION_NATIVE_GATE.acquire(blocking=False)
                if acquired:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                await asyncio.sleep(min(.01, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError()

            def decode_infer_release():
                try:
                    with self._decode_image_bounded(image_input) as image:
                        model, processor = model_registry.get_vision_stack()
                        device = next(model.parameters()).device
                        inputs = processor(images=image, return_tensors="pt")
                        inputs = {key: value.to(device) for key, value in inputs.items()}
                        if device.type == "cuda":
                            inputs = {key: tensor.to(dtype=torch.float16) if torch.is_floating_point(tensor)
                                      else tensor for key, tensor in inputs.items()}
                        with torch.no_grad():
                            features = F.normalize(model.get_image_features(**inputs), p=2, dim=-1)
                        return cast(List[float], features[0].detach().cpu().tolist())
                finally:
                    _VISION_NATIVE_GATE.release()

            future = asyncio.get_running_loop().run_in_executor(None, decode_infer_release)
            submitted = True
            future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
            return await asyncio.wait_for(asyncio.shield(future), timeout=remaining)
        except asyncio.TimeoutError as exc:
            raise ExternalDependencyError("image embedding timed out") from exc
        finally:
            if acquired and not submitted:
                _VISION_NATIVE_GATE.release()

    async def _legacy_encode_image_to_vector(self, image_input: str) -> List[float]:
        pil_image = self._decode_image_bounded(image_input)

        async with self._image_inference_semaphore:
            model, processor = model_registry.get_vision_stack()
            device = next(model.parameters()).device

            def _infer() -> List[float]:
                inputs = processor(images=pil_image, return_tensors="pt")
                inputs = {key: value.to(device) for key, value in inputs.items()}

                if device.type == "cuda":
                    inputs = {
                        key: tensor.to(dtype=torch.float16) if torch.is_floating_point(tensor) else tensor
                        for key, tensor in inputs.items()
                    }

                with torch.no_grad():
                    features = model.get_image_features(**inputs)
                    features = F.normalize(features, p=2, dim=-1)
                return cast(List[float], features[0].detach().cpu().tolist())

            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(_infer),
                    timeout=self.limits.vector_search_timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                raise ExternalDependencyError("image embedding timed out") from exc

    async def _fetch_products_by_ids(self, ids: Sequence[Union[str, int]]) -> List[Product]:
        if not ids:
            return []

        ids_str = [str(item) for item in ids]
        try:
            response = await self.opensearch_client.mget(
                index=PRODUCT_SEARCH_INDEX,
                body={"ids": ids_str},
                request_timeout=self.limits.opensearch_timeout_seconds,
            )
        except Exception as exc:
            raise ExternalDependencyError("opensearch mget failed") from exc

        product_map: Dict[str, Product] = {}
        for doc in response.get("docs", []):
            if not doc.get("found"):
                continue

            source = doc.get("_source", {})
            try:
                product = Product(
                    id=doc["_id"],
                    name=source.get("name", "Unknown"),
                    description=source.get("description", ""),
                    price=float(source.get("price", 0.0)),
                    image_url=source.get("image_url", ""),
                    category=source.get("category", "Unknown"),
                    rating=float(source.get("rating", 0.0)),
                )
                product_map[str(product.id)] = product
            except Exception:
                logger.warning("failed to materialize product from opensearch source", extra={"id": str(doc.get("_id"))}, exc_info=True)

        return [product_map[document_id] for document_id in ids_str if document_id in product_map]

    async def _fetch_products_from_db_by_ids(self, db: AsyncSession, ids: Sequence[int]) -> List[Product]:
        if not ids:
            return []

        unique_ids = list(dict.fromkeys(int(item) for item in ids))
        statement = select(Product).where(col(Product.id).in_(unique_ids)).execution_options(populate_existing=True)
        rows = list((await db.execute(statement)).scalars().all())
        by_id = {int(product.id): product for product in rows}
        return [by_id[item_id] for item_id in unique_ids if item_id in by_id]

    @staticmethod
    def _filter_products(products: Sequence[Product], filters: SearchFilter) -> List[Product]:
        """Recheck indexed/cache hits against current database catalog facts."""
        excluded = set(filters.excluded_ids or [])
        return [product for product in products
                if not is_catalog_hidden(product) and product.is_active and product.id not in excluded
                and (filters.price_min is None or product.price >= filters.price_min)
                and (filters.price_max is None or product.price <= filters.price_max)
                and (not filters.category or product.category == filters.category)]

    async def _fallback_sql_search(
        self, db: AsyncSession, query: str, limit: int = 20,
        filters: Optional[SearchFilter] = None,
    ) -> List[Product]:
        try:
            clean_query = _sanitize_query_text(query, self.limits.max_query_length)
        except ValidationError:
            return []

        search_term = f"%{clean_query}%"

        try:
            statement = (
                select(Product)
                .where(
                    or_(
                        col(Product.name).ilike(search_term),
                        col(Product.description).ilike(search_term),
                        col(Product.category).ilike(search_term),
                    )
                )
                .order_by(col(Product.rating).desc())
                .limit(limit)
            )
            filters = filters or SearchFilter()
            statement = statement.where(Product.is_active.is_(True),*real_catalog_predicates(Product))
            if filters.price_min is not None:
                statement = statement.where(Product.price >= filters.price_min)
            if filters.price_max is not None:
                statement = statement.where(Product.price <= filters.price_max)
            if filters.category:
                statement = statement.where(Product.category == filters.category)
            if filters.excluded_ids:
                statement = statement.where(col(Product.id).notin_(filters.excluded_ids))
            return list((await db.execute(statement)).scalars().all())
        except Exception:
            logger.exception("sql fallback search failed", extra={"query": clean_query, "limit": limit})
            return []

    async def ensure_opensearch_index(self) -> None:
        index_name = PRODUCT_SEARCH_INDEX
        try:
            exists = await self.opensearch_client.indices.exists(index=index_name)
            if exists:
                return

            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                        "analysis": {
                            "analyzer": {
                                "universal_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": ["lowercase", "stop", "snowball"],
                                }
                            }
                        },
                    }
                },
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "name": {"type": "text", "analyzer": "universal_analyzer"},
                        "description": {"type": "text", "analyzer": "universal_analyzer"},
                        "category": {"type": "keyword"},
                        "tags": {"type": "text", "analyzer": "universal_analyzer"},
                        "price": {"type": "float"},
                        "rating": {"type": "float"},
                        "image_url": {"type": "keyword", "index": False},
                    }
                },
            }

            await self.opensearch_client.indices.create(index=index_name, body=index_body)
            logger.info("opensearch index created", extra={"index": index_name})

        except Exception as exc:
            logger.exception("opensearch index ensure failed", extra={"index": index_name})
            raise BootstrapError(f"failed to ensure opensearch index {index_name}") from exc

    async def remember_user_fact(self, user_id: int, fact_text: str) -> None:
        await self.bootstrap()

        if user_id <= 0:
            raise ValidationError("user_id must be > 0")
        if not fact_text or not fact_text.strip():
            return

        normalized_fact = _normalize_whitespace(fact_text)
        if len(normalized_fact) > self.limits.max_memory_fact_length:
            normalized_fact = normalized_fact[: self.limits.max_memory_fact_length]

        try:
            vector = await self._get_query_embedding(normalized_fact)
            payload = [{
                "user_id": int(user_id),
                "vector": vector,
                "fact_text": normalized_fact,
                "timestamp": int(time.time()),
            }]

            async with self._vector_search_semaphore:
                await asyncio.to_thread(
                    self.milvus_client.insert,
                    collection_name=self.user_memory_collection,
                    data=payload,
                )

            logger.info("user fact remembered", extra={"user_id": user_id})

        except Exception:
            logger.exception("memory anchoring failed", extra={"user_id": user_id})

    async def recall_relevant_facts(self, user_id: int, query: str, limit: int = 5) -> List[str]:
        await self.bootstrap()

        if user_id <= 0 or limit <= 0:
            return []
        if not query or not query.strip():
            return []

        try:
            vector = await self._get_query_embedding(query)
            search_filter = f"user_id == {int(user_id)}"

            async with self._vector_search_semaphore:
                results = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.milvus_client.search,
                        collection_name=self.user_memory_collection,
                        data=[vector],
                        filter=search_filter,
                        limit=limit,
                        output_fields=["fact_text"],
                        search_params={"metric_type": "COSINE", "params": {"ef": 64}},
                    ),
                    timeout=self.limits.vector_search_timeout_seconds,
                )

            if not results or not results[0]:
                return []

            facts = []
            for hit in results[0]:
                distance = float(hit.get("distance", 0.0))
                entity = hit.get("entity", {})
                fact = entity.get("fact_text")
                if fact and distance >= self.limits.memory_similarity_threshold:
                    facts.append(str(fact))

            return facts

        except Exception:
            logger.exception("memory recall failed", extra={"user_id": user_id})
            return []


def get_embedding_model() -> SentenceTransformer:
    return model_registry.get_text_model()


_TEXT_STARTUP_FUTURES = weakref.WeakKeyDictionary()


async def initialize_query_embeddings() -> SentenceTransformer:
    # Reuse a still-running native attempt instead of queueing more loader
    # threads after caller deadlines. A completed failed attempt can retry.
    loop = asyncio.get_running_loop()
    future = _TEXT_STARTUP_FUTURES.get(loop)
    if future is None or future.done():
        future = loop.run_in_executor(None, get_embedding_model)
        future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        _TEXT_STARTUP_FUTURES[loop] = future
    budget = get_core_settings().TEXT_STARTUP_BUDGET_SECONDS
    # Retain compatibility with explicit test/operational deadline overrides.
    if STARTUP_MODEL_BUDGET_SECONDS != 360.0:
        budget = STARTUP_MODEL_BUDGET_SECONDS
    try:
        return await asyncio.wait_for(asyncio.shield(future), timeout=budget)
    except asyncio.TimeoutError as exc:
        model_registry.reject_text_startup()
        logger.error("text model startup deadline exceeded; readiness rejected")
        raise TextEmbeddingWarmupError("Text model startup deadline exceeded") from exc


class MilvusConnectionError(RuntimeError):
    """Raised when Milvus cannot be reached after exhausting retry policy."""


def _compute_backoff_delay(
    *,
    attempt: int,
    policy: MilvusRetryPolicy,
) -> float:
    raw_delay = min(
        policy.base_delay_seconds * (policy.backoff_multiplier ** (attempt - 1)),
        policy.max_delay_seconds,
    )
    jitter_window = raw_delay * policy.jitter_ratio
    return max(0.0, raw_delay + random.uniform(-jitter_window, jitter_window))


def _build_milvus_client(
    *,
    uri: str,
    token: Optional[str],
    timeout: float,
) -> MilvusClient:
    return MilvusClient(
        uri=uri,
        token=token,
        timeout=timeout,
    )


def _is_retryable_milvus_error(exc: Exception) -> bool:
    message = str(exc).lower()
    retryable_markers = (
        "timed out",
        "timeout",
        "connection refused",
        "temporarily unavailable",
        "unavailable",
        "not ready",
        "try again",
        "deadline exceeded",
    )
    return any(marker in message for marker in retryable_markers)


def connect_milvus_with_retry(
    settings: CoreSettings,
    *,
    policy: MilvusRetryPolicy = MilvusRetryPolicy(),
) -> MilvusClient:
    token = settings.MILVUS_TOKEN.get_secret_value() if settings.MILVUS_TOKEN else None
    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            client = _build_milvus_client(
                uri=str(settings.MILVUS_URI),
                token=token,
                timeout=policy.connect_timeout_seconds,
            )

            logger.info(
                "Milvus client created successfully.",
                extra={
                    "component": "milvus",
                    "attempt": attempt,
                    "uri": str(settings.MILVUS_URI),
                },
            )
            return client

        except Exception as exc:
            last_error = exc

            if not _is_retryable_milvus_error(exc) or attempt == policy.max_attempts:
                logger.exception(
                    "Milvus connection failed.",
                    extra={
                        "component": "milvus",
                        "attempt": attempt,
                        "max_attempts": policy.max_attempts,
                        "retryable": _is_retryable_milvus_error(exc),
                    },
                )
                break

            delay = _compute_backoff_delay(attempt=attempt, policy=policy)
            logger.warning(
                "Milvus connection attempt failed; retrying.",
                extra={
                    "component": "milvus",
                    "attempt": attempt,
                    "max_attempts": policy.max_attempts,
                    "sleep_seconds": round(delay, 3),
                },
            )
            time.sleep(delay)

    raise MilvusConnectionError(
        f"Unable to establish Milvus connection after {policy.max_attempts} attempts."
    ) from last_error


def get_milvus_client(
    settings: CoreSettings = Depends(get_core_settings),
) -> MilvusClient:
    return connect_milvus_with_retry(settings)

async def get_opensearch_client(
    settings: CoreSettings = Depends(get_core_settings),
) -> AsyncGenerator[AsyncOpenSearch, None]:
    client = AsyncOpenSearch(
        hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
        use_ssl=settings.OPENSEARCH_USE_SSL,
        verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
        ssl_show_warn=False,
        http_auth=(
            settings.OPENSEARCH_USER,
            settings.OPENSEARCH_PASS.get_secret_value(),
        )
        if settings.OPENSEARCH_USER and settings.OPENSEARCH_PASS
        else None,
        request_timeout=120,
        retry_on_timeout=True,
        max_retries=5,
        pool_maxsize=20,
    )
    try:
        yield client
    finally:
        await client.close()


async def get_ai_commerce_engine(
    opensearch_client: AsyncOpenSearch = Depends(get_opensearch_client),
    milvus_client: MilvusClient = Depends(get_milvus_client),
    embedding_model: SentenceTransformer = Depends(get_embedding_model),
    cache_client: IAsyncCacheClient = Depends(get_cache_client),
) -> AICommerceEngine:
    if not milvus_client or not opensearch_client:
        raise RuntimeError("AI infrastructure is offline")

    engine = AICommerceEngine(
        opensearch_client=opensearch_client,
        milvus_client=milvus_client,
        embedding_model=embedding_model,
        cache_client=cache_client,
    )
    await engine.bootstrap()
    return engine
