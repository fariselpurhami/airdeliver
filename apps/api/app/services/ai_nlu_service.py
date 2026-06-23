# apps/api/app/services/ai_nlu_service.py

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Set, Tuple, Union

from sentence_transformers import util
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import AsyncSessionFactory
from app.models.product import Product
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.services.ai_meta_cognition import MetaCognitionLayer
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService
from app.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger("airdeliver.nlu")


# =============================================================================
# CONSTANTS / CONFIG / ENUMS
# =============================================================================

class MessageType(str, Enum):
    CHAT_MESSAGE = "CHAT_MESSAGE"
    WELCOME_INTENT = "WELCOME_INTENT"
    CANCEL_INTENT = "CANCEL_INTENT"


class UiPayloadType(str, Enum):
    TEXT = "text"
    ERROR = "error"
    TYPING = "typing"
    PRODUCT_CAROUSEL = "product_carousel"
    PROACTIVE_SUGGESTION = "proactive_suggestion"
    LIFESTYLE_MATRIX = "lifestyle_matrix"
    CONFIRMATION_PROMPT = "confirmation_prompt"


class InternalCommand(str, Enum):
    ADD_BY_ID = "__INTERNAL_ADD_BY_ID__"
    REMOVE_BY_ID = "__INTERNAL_REMOVE_BY_ID__"
    CLEAR_CART = "__INTERNAL_CLEAR_CART__"
    CONFIRM_ORDER = "__INTERNAL_CONFIRM_ORDER__"
    SAVE_FOR_LATER = "__INTERNAL_SAVE_FOR_LATER__"
    GET_INITIAL_SUGGESTIONS = "__INTERNAL_GET_INITIAL_SUGGESTIONS__"
    RESET_SESSION = "__INTERNAL_RESET_SESSION__"


@dataclass(frozen=True)
class MatrixConfig:
    max_items_per_row: int = 10
    trending_pool_limit: int = 50
    deals_min_rating: float = 40.0
    stream_delay_sec: float = 0.8
    default_spending_tier: str = "MEDIUM"

    seen_cache_ttl_sec: int = 3600
    chat_history_ttl_sec: int = 86400
    chat_history_limit: int = 30
    context_window_size: int = 8
    request_lock_ttl_sec: int = 5
    user_dna_ttl_sec: int = 300

    min_intent_confidence: float = 200
    interceptor_threshold: float = 200
    max_results_search: int = 200
    max_final_products: int = 180
    max_recovery_products: int = 200
    max_visual_candidates: int = 200

    image_max_bytes: int = 5_000_000
    image_analysis_timeout_sec: float = 180.0
    search_timeout_sec: float = 180.0
    web_search_timeout_sec: float = 100.0
    llm_timeout_sec: float = 180.0
    behavior_timeout_sec: float = 15.0
    embedding_timeout_sec: float = 180.0

    max_prompt_chars: int = 4000
    max_web_context_chars: int = 1900
    max_product_desc_chars: int = 400
    max_safe_fallback_query_chars: int = 50

    no_markdown_guard: str = (
        "STRICT RULE: ZERO MARKDOWN. "
        "DO NOT use asterisks (**), hashes (#), dashes (-) or underscores (_). "
        "Use ONLY plain text. "
        "IMPORTANT: When listing features, strictly use the thick bullet symbol '●' at the start of each feature."
    )

    internal_prefix: str = "__"

    copy_bestsellers: str = "Discover our most acclaimed products."
    copy_trending: str = "Explore what is trending right now."
    copy_deals: str = "Explore curated products with strong value."
    copy_fallback: str = "Welcome! Ask me about any product."


CONFIG = MatrixConfig()


# =============================================================================
# TYPE CONTRACTS & DTOs
# =============================================================================

ProductLike = Union[Product, Mapping[str, Any]]


class SupportsModelDump(Protocol):
    def model_dump(self, *, mode: str = "python") -> Dict[str, Any]:
        ...


@dataclass(frozen=True)
class SearchConstraints:
    clean_query: str
    price_max: Optional[float] = None
    price_min: Optional[float] = None
    excluded_keywords: Tuple[str, ...] = ()
    required_specs: Mapping[str, int] = field(default_factory=dict)
    category_filter: Optional[str] = None
    intent_vibe: str = "neutral"

    def to_filters(self) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        if self.price_max is not None:
            filters["price_max"] = self.price_max
        if self.price_min is not None:
            filters["price_min"] = self.price_min
        if self.category_filter:
            filters["category"] = self.category_filter
        if self.excluded_keywords:
            filters["excluded_keywords"] = list(self.excluded_keywords)
        return filters


@dataclass(frozen=True)
class MemoryEvent:
    role: str
    content: str
    intent: str
    timestamp: str

    @staticmethod
    def create(role: str, content: str, intent: str) -> "MemoryEvent":
        return MemoryEvent(
            role=role,
            content=content.strip(),
            intent=intent.strip() or "general",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def to_json(self) -> str:
        return json.dumps(
            {"r": self.role, "c": self.content, "i": self.intent, "t": self.timestamp},
            ensure_ascii=False,
        )

    @staticmethod
    def from_raw(raw: Union[str, bytes]) -> Optional["MemoryEvent"]:
        try:
            payload = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            obj = json.loads(payload)
            return MemoryEvent(
                role=str(obj.get("r", "")).strip(),
                content=str(obj.get("c", "")).strip(),
                intent=str(obj.get("i", "general")).strip(),
                timestamp=str(obj.get("t", "")),
            )
        except Exception:
            return None


@dataclass(frozen=True)
class IncomingMessage:
    user_id: int
    msg_type: MessageType
    message_text: str
    lower_text: str
    image_b64: Optional[str]
    client_msg_id: str
    raw_payload: Mapping[str, Any]


@dataclass(frozen=True)
class UserDNA:
    tier: str = "MEDIUM"
    persona: str = "explorer"
    source: str = "fallback"

    @staticmethod
    def from_dict(data: Optional[Mapping[str, Any]]) -> "UserDNA":
        if not isinstance(data, Mapping):
            return UserDNA()
        return UserDNA(
            tier=str(data.get("tier", "MEDIUM")).upper(),
            persona=str(data.get("persona", "explorer")),
            source=str(data.get("source", "fallback")),
        )


@dataclass(frozen=True)
class RequestContext:
    user_id: int
    correlation_id: str
    received_at: float


@dataclass(frozen=True)
class SearchPlan:
    search_query: str
    vision_description: str
    constraints: SearchConstraints
    is_specs_query: bool
    is_broad_query: bool


@dataclass(frozen=True)
class LlmDecision:
    response_text: str
    products: Tuple[ProductLike, ...]
    response_type: UiPayloadType
    reason: str


@dataclass(frozen=True)
class ParsedInternalCommand:
    name: InternalCommand
    argument: Optional[str] = None


@dataclass(frozen=True)
class CommandMatch:
    handled: bool
    action: Optional[str] = None
    normalized_text: str = ""
    extracted_query: str = ""


@dataclass(frozen=True)
class StrategicSearchResult:
    products: List[Any]
    matched_tier: str
    query_used: str


# =============================================================================
# HELPER FUNCTIONS (Pure Utilities)
# =============================================================================

def _utc_timestamp() -> float:
    return datetime.now(timezone.utc).timestamp()


def _safe_product_get(product: Any, field: str, default: Any = "") -> Any:
    if isinstance(product, Mapping):
        return product.get(field, default) or default
    return getattr(product, field, default) or default


def _safe_product_dump(product: Any) -> Dict[str, Any]:
    if hasattr(product, "model_dump"):
        return product.model_dump(mode="json")
    if isinstance(product, Mapping):
        return dict(product)
    return {
        "id": getattr(product, "id", None),
        "name": getattr(product, "name", None),
        "brand": getattr(product, "brand", None),
        "category": getattr(product, "category", None),
        "description": getattr(product, "description", None),
        "price": getattr(product, "price", None),
        "rating": getattr(product, "rating", None),
        "image_url": getattr(product, "image_url", None),
    }


def _sanitize_free_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_search_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _deduplicate_products(products: Sequence[Any]) -> List[Any]:
    seen_ids: Set[Any] = set()
    unique: List[Any] = []

    for product in products:
        product_id = _safe_product_get(product, "id", None)
        if product_id in seen_ids:
            continue
        seen_ids.add(product_id)
        unique.append(product)

    return unique


def _extract_command_argument(command: str, prefix: str) -> Optional[str]:
    if not command.startswith(prefix):
        return None
    parts = command.split(":", 1)
    if len(parts) != 2:
        return None
    argument = parts[1].strip()
    return argument or None


def _parse_internal_command(command: str) -> Optional[ParsedInternalCommand]:
    command = str(command or "").strip()

    if command.startswith(f"{InternalCommand.ADD_BY_ID.value}:"):
        arg = _extract_command_argument(command, InternalCommand.ADD_BY_ID.value)
        return ParsedInternalCommand(name=InternalCommand.ADD_BY_ID, argument=arg)

    if command.startswith(f"{InternalCommand.REMOVE_BY_ID.value}:"):
        arg = _extract_command_argument(command, InternalCommand.REMOVE_BY_ID.value)
        return ParsedInternalCommand(name=InternalCommand.REMOVE_BY_ID, argument=arg)

    exact_commands = {
        InternalCommand.CLEAR_CART.value: InternalCommand.CLEAR_CART,
        InternalCommand.CONFIRM_ORDER.value: InternalCommand.CONFIRM_ORDER,
        InternalCommand.SAVE_FOR_LATER.value: InternalCommand.SAVE_FOR_LATER,
        InternalCommand.GET_INITIAL_SUGGESTIONS.value: InternalCommand.GET_INITIAL_SUGGESTIONS,
        InternalCommand.RESET_SESSION.value: InternalCommand.RESET_SESSION,
    }

    if command in exact_commands:
        return ParsedInternalCommand(name=exact_commands[command])

    return None


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _strip_trigger_prefixes(text: str, triggers: Sequence[str]) -> str:
    clean = text
    for trigger in triggers:
        clean = clean.replace(trigger, " ")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


# =============================================================================
# SERIALIZATION / SANITIZATION
# =============================================================================

class SafeJson:
    @staticmethod
    def default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        return str(obj)

    @staticmethod
    def dumps(data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, default=SafeJson.default)


class TextSanitizer:
    _strip_markdown_symbols = re.compile(r"[\*\_\"`#\-]")
    _allow_pattern = re.compile(
        r"[^\w\s\u0600-\u06FF\.,!?:;\(\)\[\]%\$\£\€\'’\/\+\n\u25CF]",
        re.UNICODE,
    )
    _collapse_many_newlines = re.compile(r"\n{3,}")
    _collapse_spaces = re.compile(r"[ \t]{2,}")
    _currency_gap = re.compile(r"([\$£€])[\s\n]+(\d)")
    _punctuation_gap = re.compile(r"\s+([,;:!?])")

    # السر هنا: التقاط نهاية الجملة (نقطة وبعدها مسافة وحرف)
    _sentence_break = re.compile(r"([.!?])\s+(?=[A-Z\u0600-\u06FF])")
    # التقاط النقطة العريضة لإجبارها على سطر جديد
    _bullet_break = re.compile(r"(?<!\n)\s*(●)")

    @classmethod
    def sanitize_response_text(cls, raw_text: str) -> str:
        text = str(raw_text or "")
        text = cls._strip_markdown_symbols.sub("", text)
        text = cls._allow_pattern.sub(" ", text)

        # إجبار أي نقطة عريضة تنزل في سطر جديد قبلها
        text = cls._bullet_break.sub(r"\n\n\1 ", text)

        # إجبار أي نقطة في نهاية الجملة إنها تنزل سطرين 
        text = cls._sentence_break.sub(r"\1\n\n", text)

        text = text.replace("●", "● ").replace("●  ", "● ")
        text = cls._currency_gap.sub(r"\1\2", text)
        text = cls._punctuation_gap.sub(r"\1", text)

        lines = [cls._collapse_spaces.sub(" ", line).strip() for line in text.split("\n")]
        text = "\n".join(lines).strip()
        text = cls._collapse_many_newlines.sub("\n\n", text)
        return text


# =============================================================================
# KEYSPACE
# =============================================================================

class RedisKeys:
    @staticmethod
    def idempotency(client_msg_id: str) -> str:
        return f"nlu:idemp:{client_msg_id}"

    @staticmethod
    def ui_channel(user_id: int) -> str:
        return f"airdeliver:response:{user_id}"

    @staticmethod
    def chat_history(user_id: int) -> str:
        return f"airdeliver:v2:session:{user_id}:chat_history"

    @staticmethod
    def seen_products(user_id: int) -> str:
        return f"airdeliver:v2:session:{user_id}:seen_products"

    @staticmethod
    def user_dna(user_id: int) -> str:
        return f"dna:profile:{user_id}"

    @staticmethod
    def ghost_profile(user_id: int) -> str:
        return f"u:{user_id}:ghost_v2"

    @staticmethod
    def cart(user_id: int) -> str:
        return f"ai_cart:{user_id}"


# =============================================================================
# LOW-LEVEL SAFE ACCESS
# =============================================================================

class ProductAccess:
    @staticmethod
    def get(obj: ProductLike, attr: str, default: Any = "") -> Any:
        if isinstance(obj, Mapping):
            return obj.get(attr, default) or default
        return getattr(obj, attr, default) or default

    @staticmethod
    def dump(obj: ProductLike) -> Dict[str, Any]:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if isinstance(obj, Mapping):
            return dict(obj)
        return {
            "id": getattr(obj, "id", None),
            "name": getattr(obj, "name", None),
            "brand": getattr(obj, "brand", None),
            "category": getattr(obj, "category", None),
            "description": getattr(obj, "description", None),
            "price": str(getattr(obj, "price", None)) if getattr(obj, "price", None) is not None else None,
            "rating": getattr(obj, "rating", None),
            "image_url": getattr(obj, "image_url", None),
        }


# =============================================================================
# OBSERVABILITY
# =============================================================================

class StructuredLog:
    @staticmethod
    def info(event: str, **fields: Any) -> None:
        logger.info("%s | %s", event, SafeJson.dumps(fields))

    @staticmethod
    def warning(event: str, **fields: Any) -> None:
        logger.warning("%s | %s", event, SafeJson.dumps(fields))

    @staticmethod
    def error(event: str, **fields: Any) -> None:
        logger.error("%s | %s", event, SafeJson.dumps(fields))

    @staticmethod
    def exception(event: str, **fields: Any) -> None:
        logger.exception("%s | %s", event, SafeJson.dumps(fields))


# =============================================================================
# INFRA ADAPTERS
# =============================================================================

class BoundedTaskSupervisor:
    def __init__(self) -> None:
        self._tasks: Set[asyncio.Task[Any]] = set()

    def create_task(self, coro: Any) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)

        def _done(t: asyncio.Task[Any]) -> None:
            self._tasks.discard(t)
            try:
                _ = t.exception()
            except asyncio.CancelledError:
                return
            except Exception:
                StructuredLog.exception("background_task_completion_failure")

        task.add_done_callback(_done)


class IdempotencyGuard:
    def __init__(self, cache: IAsyncCacheClient, ttl_seconds: int) -> None:
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def acquire(self, key: str) -> bool:
        try:
            if hasattr(self._cache, "client") and self._cache.client is not None:
                client = self._cache.client
                if hasattr(client, "set"):
                    result = await client.set(key, "1", ex=self._ttl_seconds, nx=True)
                    return bool(result)
        except Exception as exc:
            StructuredLog.warning("idempotency_atomic_set_unavailable", error=str(exc))

        try:
            existing = await self._cache.get(key)
            if existing:
                return False
            await self._cache.set(key, "1")
            try:
                if hasattr(self._cache, "expire"):
                    await self._cache.expire(key, self._ttl_seconds)
                elif hasattr(self._cache, "client") and hasattr(self._cache.client, "expire"):
                    await self._cache.client.expire(key, self._ttl_seconds)
            except Exception:
                pass
            return True
        except Exception as exc:
            StructuredLog.warning("idempotency_fail_open", error=str(exc))
            return True


class MemoryStore:
    def __init__(self, cache: IAsyncCacheClient, config: MatrixConfig) -> None:
        self._cache = cache
        self._config = config

    async def append(self, user_id: int, event: MemoryEvent) -> None:
        key = RedisKeys.chat_history(user_id)
        try:
            pipeline = self._cache.client.pipeline()
            pipeline.lpush(key, event.to_json())
            pipeline.ltrim(key, 0, self._config.chat_history_limit - 1)
            pipeline.expire(key, self._config.chat_history_ttl_sec)
            await pipeline.execute()
        except Exception as exc:
            StructuredLog.error("memory_append_failed", user_id=user_id, error=str(exc))

    async def get_context(self, user_id: int, limit: int) -> str:
        key = RedisKeys.chat_history(user_id)
        try:
            raw_items = await self._cache.client.lrange(key, 0, max(limit - 1, 0))
            if not raw_items:
                return ""
            timeline: List[str] = []
            for raw in reversed(raw_items):
                event = MemoryEvent.from_raw(raw)
                if not event:
                    continue
                role = "Customer" if event.role == "u" else "Agent"
                timeline.append(f"{role}: {event.content}")
            return "\n".join(timeline)
        except Exception as exc:
            StructuredLog.warning("memory_recall_failed", user_id=user_id, error=str(exc))
            return ""


class UiGateway:
    def __init__(self, cache: IAsyncCacheClient) -> None:
        self._cache = cache

    async def publish(self, user_id: int, payload: Dict[str, Any], correlation_id: str) -> None:
        channel = RedisKeys.ui_channel(user_id)
        envelope = dict(payload)
        envelope["meta"] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": "diamond_nlu_ultra_v1",
            "engine_status": "online",
            "correlation_id": correlation_id,
        }
        message = SafeJson.dumps(envelope)
        await self._cache.publish(channel, message)


class UserDnaStore:
    def __init__(self, cache: IAsyncCacheClient, behavior_engine: Optional[BehaviorEngine], config: MatrixConfig) -> None:
        self._cache = cache
        self._behavior_engine = behavior_engine
        self._config = config

    async def get(self, user_id: int) -> UserDNA:
        cache_key = RedisKeys.user_dna(user_id)

        try:
            if hasattr(self._cache, "get_json"):
                cached = await self._cache.get_json(cache_key)
                if cached:
                    return UserDNA.from_dict(cached)
        except Exception:
            pass

        default = UserDNA()

        try:
            if not self._behavior_engine or not hasattr(self._behavior_engine, "get_user_profile"):
                return default

            profile = await asyncio.wait_for(
                self._behavior_engine.get_user_profile(user_id),
                timeout=self._config.behavior_timeout_sec,
            )

            if isinstance(profile, Mapping):
                data = dict(profile)
                data["source"] = "engine"
                try:
                    if hasattr(self._cache, "set_json"):
                        await self._cache.set_json(cache_key, data, ttl=self._config.user_dna_ttl_sec)
                except Exception:
                    pass
                return UserDNA.from_dict(data)

        except asyncio.TimeoutError:
            StructuredLog.warning("user_dna_timeout", user_id=user_id)
        except Exception as exc:
            StructuredLog.error("user_dna_failure", user_id=user_id, error=str(exc))

        return default


# =============================================================================
# DOMAIN COMPONENTS
# =============================================================================

class DiamondInterceptor:
    AGGRESSIVE_STOPWORDS: Set[str] = {
        "i", "need", "want", "looking", "for", "can", "run", "is", "a", "an", "the",
        "with", "without", "buy", "find", "get", "search", "could", "would", "be",
        "have", "has", "do", "does", "that", "of", "in", "on", "at", "to", "from",
        "by", "and", "or", "but", "so", "extremely", "enough", "also", "it",
        "maintain", "possible", "after", "two", "years", "what", "should", "choose",
        "right", "now", "trade-offs", "official", "current", "availability", "specs",
        "review", "heavy", "light", "workloads", "silent", "battery", "price", "cost",
        "budget", "cheap", "expensive", "best", "top", "recommend", "suggestion",
        "vs", "versus", "better", "than",
        "عايز", "محتاج", "ابحث", "عن", "لو", "سمحت", "ممكن", "من", "فضلك",
        "بالله", "الي", "اللي", "ده", "دي",
    }

    def __init__(self, matcher_threshold: float) -> None:
        self.matcher_threshold = matcher_threshold

    def _distill_signal(self, text: str) -> Set[str]:
        clean_text = re.sub(r"[^\w\s]", "", text.lower())
        return {
            word for word in clean_text.split()
            if len(word) > 2 and word not in self.AGGRESSIVE_STOPWORDS
        }

    def validate_alignment(self, user_query: str, top_candidate: ProductLike, nlu_intent: Optional[str] = None) -> float:
        category = str(ProductAccess.get(top_candidate, "category", "")).lower().strip()
        name = str(ProductAccess.get(top_candidate, "name", "")).lower().strip()
        brand = str(ProductAccess.get(top_candidate, "brand", "")).lower().strip()

        if nlu_intent and nlu_intent != "UNKNOWN":
            normalized_intent = nlu_intent.lower()
            if normalized_intent in category or normalized_intent in name:
                return 1.0

        user_signal = self._distill_signal(user_query)
        if not user_signal:
            return 1.0

        signature = f"{name} {category} {brand}"
        hits = 0
        for word in user_signal:
            if word in signature:
                hits += 1
            elif word.endswith("s") and word[:-1] in signature:
                hits += 1
            elif f"{word}s" in signature:
                hits += 1

        denominator = max(1, min(len(user_signal), 3))
        score = hits / denominator

        if score < self.matcher_threshold:
            StructuredLog.warning(
                "alignment_below_threshold",
                score=round(score, 4),
                product=name,
                signal=list(user_signal)[:5],
            )

        return score


class ConstraintExtractor:
    ignored_anchors: Set[str] = {
        "one", "thing", "product", "item", "device", "best", "cheap", "top", "good",
        "monster", "beast", "now", "today", "asap", "quickly", "immediately", "here", "please"
    }

    comparison_markers: Tuple[str, ...] = (
        "why", "better", " vs ", "compare", "difference", "which",
        "ليه", "أحسن", "مقارنة", "الفرق",
    )

    negation_triggers: Tuple[str, ...] = (
        "no", "not", "exclude", "without", "don't want", "hate",
        "don't like", "dislike", "avoid", "never", "except",
    )

    open_budget_triggers: Tuple[str, ...] = (
        "budget is open", "no limit", "price is open", "unlimited",
        "money is no object", "open budget", "no price limit",
    )

    price_trigger_pattern = r"(?:max|under|below|limit|budget|bugdet|budjet|price|cost|ceiling)"

    intent_patterns: Tuple[str, ...] = (
        r"(?:want|need|buy|get|looking for|search for|find|recommend)\s+(?:a|an|the|some|new|best|top|cheap)?\s*([a-zA-Z0-9\s\-]+?)(?:\s+(?:for|with|under|below|that|which|in|at|from|priced)|$|[.,])",
        r"^([a-zA-Z0-9\s\-]+?)\s+(?:with|under|below|max|for|containing)",
    )

    def extract(self, text: str) -> SearchConstraints:
        original = text.strip()
        lower_text = original.lower()

        clean_query = lower_text
        category_filter: Optional[str] = None
        price_max: Optional[float] = None
        price_min: Optional[float] = None
        excluded_keywords: List[str] = []
        required_specs: Dict[str, int] = {}
        intent_vibe = "neutral"

        for pattern in self.intent_patterns:
            match = re.search(pattern, lower_text)
            if not match:
                continue
            raw_phrase = match.group(1).strip()
            words = raw_phrase.split()
            if not words:
                continue
            candidate = words[-1]
            singular = candidate[:-1] if candidate.endswith("s") and len(candidate) > 3 else candidate
            if singular not in self.ignored_anchors and len(singular) > 2:
                category_filter = singular
                clean_query = f"{clean_query} {(singular + ' ') * 5}".strip()
                break

        if any(trigger in lower_text for trigger in self.open_budget_triggers):
            price_max = None
            for trigger in self.open_budget_triggers:
                clean_query = clean_query.replace(trigger, "")
        else:
            vibe_map = {
                "cheap": 500.0,
                "affordable": 800.0,
                "budget": 1000.0,
                "mid-range": 1500.0,
                "mid range": 1500.0,
                "economical": 600.0,
            }
            for vibe, cap in vibe_map.items():
                if vibe in lower_text and price_max is None:
                    intent_vibe = vibe
                    price_max = cap
                    break

        patterns = (
            rf"{self.price_trigger_pattern}\s*(?:is|of|at)?\s*[\$€£]?\s*(\d+(?:\.\d+)?(?:k|000)?)",
            r"(\d+(?:\.\d+)?(?:k|000)?)\s*(?:usd|dollars|bucks|eur|egp|\$)",
            r"[\$€£](\d+(?:\.\d+)?(?:k|000)?)",
        )

        for pattern in patterns:
            match = re.search(pattern, lower_text)
            if not match:
                continue
            raw_value = match.group(1)
            try:
                multiplier = 1000 if "k" in raw_value else 1
                normalized = float(raw_value.replace("k", "")) * multiplier
                if normalized > 0:
                    price_max = normalized
                    clean_query = re.sub(pattern, "", clean_query, flags=re.IGNORECASE).strip()
                    break
            except ValueError:
                pass

        if not any(marker in lower_text for marker in self.comparison_markers):
            for trigger in self.negation_triggers:
                if trigger not in lower_text:
                    continue
                pattern = rf"{re.escape(trigger)}\s+([a-zA-Z0-9_\-\s,]+)"
                match = re.search(pattern, lower_text)
                if not match:
                    continue
                raw_segment = match.group(1)
                for stop_marker in (".", " but ", " however ", " and i ", " my ", " i "):
                    if stop_marker in raw_segment:
                        raw_segment = raw_segment.split(stop_marker)[0]
                candidates = re.split(r"\s+(?:or|and|,)\s+|\s*,\s*", raw_segment)
                for item in candidates:
                    word = item.strip()
                    if len(word) > 2 and word not in {"the", "a", "an", "products", "items", "brands"}:
                        excluded_keywords.append(word)
                        clean_query = re.sub(
                            rf"\b{re.escape(word)}\b",
                            "",
                            clean_query,
                            flags=re.IGNORECASE,
                        )

        ram_match = re.search(r"(\d+)\s*(?:gb|g)\s*(?:ram|memory)", lower_text)
        if ram_match:
            required_specs["ram"] = int(ram_match.group(1))

        storage_match = re.search(r"(\d+)\s*(?:gb|tb|t)\s*(?:ssd|storage|disk)", lower_text)
        if storage_match:
            value = int(storage_match.group(1))
            token = storage_match.group(0).lower()
            if "tb" in token or re.search(r"\d+\s*t\s", f"{value} t "):
                value *= 1024
            required_specs["storage"] = value

        for junk in list(self.negation_triggers) + [
            "budget", "price", "cost", "max", "under", "limit", "is", "of", "want", "need",
            "looking for", "find"
        ]:
            clean_query = re.sub(rf"\b{re.escape(junk)}\b", "", clean_query, flags=re.IGNORECASE)

        clean_query = re.sub(r"\s+", " ", clean_query).strip()

        return SearchConstraints(
            clean_query=clean_query or original,
            price_max=price_max,
            price_min=price_min,
            excluded_keywords=tuple(dict.fromkeys(excluded_keywords)),
            required_specs=required_specs,
            category_filter=category_filter,
            intent_vibe=intent_vibe,
        )


class CandidateRanker:
    stopwords: Set[str] = {
        "best", "the", "a", "an", "i", "want", "need", "looking", "for",
        "top", "recommend", "buy", "get", "right", "now", "tell", "me",
        "please", "find", "search", "show", "what", "is", "vs", "compare",
    }

    def __init__(self, search_engine: AICommerceEngine) -> None:
        self._search_engine = search_engine

    def rerank(self, message_text: str, candidates: Sequence[ProductLike]) -> List[ProductLike]:
        if not candidates:
            return []

        clean_msg = re.sub(r"[^\w\s]", "", message_text.lower())
        query_tokens = [w for w in clean_msg.split() if w not in self.stopwords and len(w) > 1]
        scored: List[Tuple[ProductLike, float]] = []

        for prod in candidates:
            score = 0.0
            p_name = str(ProductAccess.get(prod, "name", ""))
            p_cat = str(ProductAccess.get(prod, "category", ""))
            p_brand = str(ProductAccess.get(prod, "brand", ""))
            p_rating = ProductAccess.get(prod, "rating", 0)

            p_text = f"{p_name} {p_cat} {p_brand}".lower()
            p_tokens = set(re.split(r"\W+", p_text))

            matches = 0
            for token in query_tokens:
                if token in p_tokens:
                    matches += 1
                elif token.endswith("s") and token[:-1] in p_tokens:
                    matches += 1
                elif f"{token}s" in p_tokens:
                    matches += 1

            if matches > 0:
                score += matches * 1000.0

            try:
                score += float(p_rating or 0) * 10.0
            except Exception:
                pass

            scored.append((prod, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in scored]

    def semantic_trim(self, anchor_text: str, candidates: Sequence[ProductLike], exact_match: str = "") -> List[ProductLike]:
        if not candidates:
            return []

        model = getattr(self._search_engine, "embedding_model", None)
        if model is None:
            return list(candidates[:CONFIG.max_final_products])

        try:
            anchor_emb = model.encode(anchor_text.lower(), convert_to_tensor=True)
            scored: List[Tuple[ProductLike, float]] = []

            for product in candidates:
                category = str(ProductAccess.get(product, "category", ""))
                name = str(ProductAccess.get(product, "name", ""))
                dna = f"{name} {category}".lower()
                product_emb = model.encode(dna, convert_to_tensor=True)
                score = float(util.cos_sim(anchor_emb, product_emb).item()) * 100.0
                if exact_match and exact_match.lower() in dna:
                    score += 50.0
                scored.append((product, score))

            scored.sort(key=lambda item: item[1], reverse=True)
            return [item[0] for item in scored[:CONFIG.max_final_products]]
        except Exception as exc:
            StructuredLog.warning("semantic_trim_failed", error=str(exc))
            return list(candidates[:CONFIG.max_final_products])


# =============================================================================
# MAIN SERVICE
# =============================================================================

class AINLUService:
    """
    Enterprise-grade single-file architecture.

    Internal layers:
    - Boundary validation
    - Idempotency and request context
    - Memory and UI gateways
    - Query analysis and planning
    - Search/ranking/recovery
    - Response synthesis
    - Async background telemetry
    """

    def __init__(
        self,
        db: AsyncSession,
        search_engine: AICommerceEngine,
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
        llm_service: FreeLLMService,
        behavior_engine: Optional[BehaviorEngine] = None,
    ) -> None:
        self.db = db
        self.search_engine = search_engine
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.redis = cache
        self.llm_service = llm_service
        self.behavior_engine = behavior_engine
        self.meta_cognition = MetaCognitionLayer()

        self.config = CONFIG
        self.interceptor = DiamondInterceptor(self.config.interceptor_threshold)
        self.constraint_extractor = ConstraintExtractor()
        self.ranker = CandidateRanker(search_engine)

        self.idempotency = IdempotencyGuard(cache, self.config.request_lock_ttl_sec)
        self.memory = MemoryStore(cache, self.config)
        self.ui = UiGateway(cache)
        self.user_dna_store = UserDnaStore(cache, behavior_engine, self.config)
        self.tasks = BoundedTaskSupervisor()

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    async def process_message(self, message_payload: dict) -> None:
        request = self._parse_incoming_message(message_payload)
        ctx = RequestContext(
            user_id=request.user_id,
            correlation_id=request.client_msg_id,
            received_at=time.monotonic(),
        )

        StructuredLog.info(
            "process_message_received",
            correlation_id=ctx.correlation_id,
            user_id=request.user_id,
            msg_type=request.msg_type.value,
            has_text=bool(request.message_text),
            has_image=bool(request.image_b64),
        )

        lock_key = RedisKeys.idempotency(request.client_msg_id)
        lock_acquired = await self.idempotency.acquire(lock_key)
        if not lock_acquired:
            StructuredLog.info(
                "duplicate_request_absorbed",
                correlation_id=ctx.correlation_id,
                user_id=request.user_id,
            )
            return

        if self._is_internal_command(request.message_text):
            StructuredLog.info(
                "internal_command_detected",
                correlation_id=ctx.correlation_id,
                user_id=request.user_id,
            )
            await self._process_internal_command(request.user_id, request.message_text)
            return

        if request.image_b64 is not None:
            self._validate_image_payload(request.image_b64)

        await self._send_to_ui(request.user_id, {"content": None, "type": UiPayloadType.TYPING.value}, ctx)

        if request.msg_type == MessageType.CANCEL_INTENT:
            await self._handle_cancel_intent(request, ctx)
            return

        if request.message_text:
            await self._append_to_memory(request.user_id, "u", request.message_text, intent="query")

        # Adapted call to seamlessly integrate v3's semantic command interceptor
        handled = await self._handle_text_commands(request.user_id, request.message_text, request.raw_payload)
        if handled:
            return

        vision_query, vision_description = await self._resolve_vision_query(request, ctx)
        search_query = vision_query or request.message_text

        if request.msg_type == MessageType.WELCOME_INTENT:
            matrix_routed = await self._try_route_welcome_matrix(request, ctx)
            if matrix_routed:
                return

        optimized_query = await self._optimize_search_query(search_query)
        plan = self._build_search_plan(
            optimized_query=optimized_query,
            original_message=request.message_text,
            vision_description=vision_description,
            has_image=bool(request.image_b64),
        )

        candidates, fallback_trigger, ai_response_prefix = await self._execute_search(
            request=request,
            plan=plan,
            ctx=ctx,
        )

        final_products = self._finalize_candidates(
            message_text=request.message_text,
            lower_text=request.lower_text,
            has_image=bool(request.image_b64),
            candidates=candidates,
        )

        decision = await self._synthesize_response(
            request=request,
            ctx=ctx,
            plan=plan,
            final_products=final_products,
            ai_response_prefix=ai_response_prefix,
        )

        clean_content = TextSanitizer.sanitize_response_text(decision.response_text)
        safe_products = [ProductAccess.dump(p) for p in decision.products]

        payload = {
            "content": clean_content,
            "type": decision.response_type.value,
            "products": safe_products,
            "reason": decision.reason,
        }

        await self._send_to_ui(request.user_id, payload, ctx)

        self.tasks.create_task(self._save_conversation_turn(request.user_id, request.message_text, decision.response_text))
        self.tasks.create_task(self._mark_products_as_seen(request.user_id, list(decision.products)))
        
        # Async memory extraction from v3
        self.tasks.create_task(self._bg_memorize(request.user_id, request.message_text))

        StructuredLog.info(
            "process_message_completed",
            correlation_id=ctx.correlation_id,
            user_id=request.user_id,
            response_type=decision.response_type.value,
            product_count=len(decision.products),
            latency_ms=round((time.monotonic() - ctx.received_at) * 1000, 2),
        )

    async def handle_idle_trigger(self, user_id: int) -> None:
        try:
            statement = select(Product).order_by(col(Product.rating).desc()).limit(3)
            result = await self.db.execute(statement)
            products = result.scalars().all()

            if products:
                await self._send_to_ui(
                    user_id,
                    {
                        "content": "Still thinking? Check out these top-rated items!",
                        "type": UiPayloadType.PROACTIVE_SUGGESTION.value,
                        "products": [ProductAccess.dump(p) for p in products],
                        "reason": "Idle Recovery",
                    },
                    RequestContext(user_id=user_id, correlation_id=f"idle:{user_id}:{int(time.time())}", received_at=time.monotonic()),
                )
        except Exception as exc:
            StructuredLog.error("idle_trigger_failed", user_id=user_id, error=str(exc))

    # -------------------------------------------------------------------------
    # INPUT VALIDATION
    # -------------------------------------------------------------------------

    def _parse_incoming_message(self, payload: Mapping[str, Any]) -> IncomingMessage:
        if not isinstance(payload, Mapping):
            raise ValueError("message_payload must be a mapping")

        raw_user_id = payload.get("user_id")
        try:
            user_id = int(raw_user_id)
        except Exception as exc:
            raise ValueError("user_id is required and must be an integer") from exc

        raw_type = str(payload.get("type", MessageType.CHAT_MESSAGE.value)).strip().upper()
        try:
            msg_type = MessageType(raw_type)
        except ValueError:
            msg_type = MessageType.CHAT_MESSAGE

        raw_message = payload.get("message")
        message_text = str(raw_message).strip() if raw_message is not None and not isinstance(raw_message, dict) else ""
        image_b64 = payload.get("image")
        if image_b64 is not None:
            image_b64 = str(image_b64)

        client_msg_id = self._derive_client_message_id(
            user_id=user_id,
            msg_type=msg_type.value,
            message_text=message_text,
            image_b64=image_b64,
            explicit_id=payload.get("client_msg_id"),
        )

        return IncomingMessage(
            user_id=user_id,
            msg_type=msg_type,
            message_text=message_text,
            lower_text=message_text.lower(),
            image_b64=image_b64,
            client_msg_id=client_msg_id,
            raw_payload=dict(payload),
        )

    def _derive_client_message_id(
        self,
        *,
        user_id: int,
        msg_type: str,
        message_text: str,
        image_b64: Optional[str],
        explicit_id: Any,
    ) -> str:
        if explicit_id:
            return str(explicit_id)

        img_fingerprint = image_b64[:50] if image_b64 else "void"
        raw_signature = f"{user_id}:{msg_type}:{message_text}:{img_fingerprint}"
        return hashlib.md5(raw_signature.encode("utf-8")).hexdigest()

    def _validate_image_payload(self, image_b64: str) -> None:
        if len(image_b64) > self.config.image_max_bytes:
            raise ValueError("Image too large. Max 5MB allowed.")
        try:
            base64.b64decode(image_b64, validate=False)
        except Exception as exc:
            raise ValueError("Invalid base64 image payload.") from exc

    def _is_internal_command(self, message_text: str) -> bool:
        return message_text.startswith(self.config.internal_prefix) or "INTERNAL" in message_text

    # -------------------------------------------------------------------------
    # MEMORY / UI
    # -------------------------------------------------------------------------

    async def _append_to_memory(self, user_id: int, role: str, content: str, intent: str = "general") -> None:
        await self.memory.append(user_id, MemoryEvent.create(role, content, intent))

    async def _get_conversation_context(self, user_id: int, limit: Optional[int] = None) -> str:
        return await self.memory.get_context(user_id, limit or self.config.context_window_size)

    async def _save_conversation_turn(self, user_id: int, user_msg: str, ai_msg: str) -> None:
        clean_user = user_msg.replace("\n", " ").strip()
        clean_ai = ai_msg.replace("\n", " ").strip()
        await self._append_to_memory(user_id, "u", clean_user, "general")
        await self._append_to_memory(user_id, "a", clean_ai, "general")

    async def _send_to_ui(self, user_id: int, payload: Dict[str, Any], ctx: Optional[RequestContext] = None) -> None:
        try:
            correlation_id = ctx.correlation_id if ctx else f"ui-send-{user_id}-{int(time.time())}"
            await self.ui.publish(user_id, payload, correlation_id)
        except Exception as exc:
            StructuredLog.error(
                "ui_publish_failed",
                correlation_id=ctx.correlation_id if ctx else None,
                user_id=user_id,
                error=str(exc),
            )

    async def _get_user_dna(self, user_id: int) -> UserDNA:
        return await self.user_dna_store.get(user_id)

    # -------------------------------------------------------------------------
    # INTERNAL V3 HELPERS INTEGRATED AS CLASS METHODS
    # -------------------------------------------------------------------------
    
    def _get_context_key(self, user_id: int) -> str:
        return RedisKeys.chat_history(user_id)

    def _get_seen_key(self, user_id: int) -> str:
        return RedisKeys.seen_products(user_id)

    async def _safe_publish(self, payload: Dict[str, Any], routing_key: str) -> None:
        await self.rabbitmq.publish(payload, routing_key)

    async def _safe_send_ui(self, user_id: int, payload: Dict[str, Any]) -> None:
        await self._send_to_ui(user_id, payload)

    async def _search_single_product(self, query: str, limit: int = 1) -> List[Any]:
        return await self.search_engine.perform_hybrid_search_pure(self.db, query, limit=limit)

    async def _safe_bundle_generation(self, product: Any) -> List[Any]:
        try:
            bundle = await self.search_engine.generate_perfect_bundle(self.db, product)
            if not bundle:
                return []
            return list(bundle)
        except Exception as exc:
            logger.warning("bundle_generation_failed", extra={"error": str(exc)})
            return []

    async def _safe_delete_cache_key(self, key: str) -> None:
        try:
            await self.cache.delete(key)
        except Exception as exc:
            logger.warning("cache_delete_failed", extra={"key": key, "error": str(exc)})

    # -------------------------------------------------------------------------
    # CANCEL / INTERNAL (Powered by v3 logic)
    # -------------------------------------------------------------------------

    async def _handle_cancel_intent(self, request: IncomingMessage, ctx: RequestContext) -> None:
        cancel_data = request.raw_payload.get("message", {})
        if isinstance(cancel_data, str):
            try:
                cancel_data = json.loads(cancel_data)
            except Exception:
                cancel_data = {}

        await self.rabbitmq.publish(
            {
                "user_id": request.user_id,
                "order_id": cancel_data.get("orderId"),
                "reason": cancel_data.get("reason", "discarded"),
            },
            "airdeliver.ai.intent.cancel_order",
        )

        StructuredLog.info(
            "cancel_intent_published",
            correlation_id=ctx.correlation_id,
            user_id=request.user_id,
        )

    async def _process_internal_command(self, user_id: int, command: str) -> None:
        """
        Internal bus router with strict parsing and bounded side effects (from v3).
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        parsed = _parse_internal_command(command)
        logger.info(
            "internal_command_received",
            extra={"user_id": user_id, "command": command, "parsed": parsed.name.value if parsed else None},
        )

        if parsed is None:
            logger.warning(
                "internal_command_unknown",
                extra={"user_id": user_id, "command": command},
            )
            return

        if parsed.name == InternalCommand.ADD_BY_ID:
            try:
                if parsed.argument is None:
                    raise ValueError("Missing product id")
                product_id = int(parsed.argument)

                await self._safe_publish(
                    {"user_id": user_id, "product_id": product_id, "quantity": 1, "source": "internal_command"},
                    "airdeliver.ai.cart.add",
                )
            except Exception as exc:
                logger.error(
                    "internal_add_by_id_failed",
                    extra={"user_id": user_id, "argument": parsed.argument, "error": str(exc)},
                )
            return

        if parsed.name == InternalCommand.REMOVE_BY_ID:
            try:
                if parsed.argument is None:
                    raise ValueError("Missing product id")
                product_id = int(parsed.argument)

                await self._safe_publish(
                    {
                        "user_id": user_id,
                        "product_id": product_id,
                        "action": "remove_by_id",
                        "notify_user": False,
                        "source": "internal_command",
                    },
                    "airdeliver.ai.cart.remove",
                )
                await self._perform_devilish_recovery(user_id, product_id)
            except Exception as exc:
                logger.error(
                    "internal_remove_by_id_failed",
                    extra={"user_id": user_id, "argument": parsed.argument, "error": str(exc)},
                )
            return

        if parsed.name == InternalCommand.CLEAR_CART:
            await self._safe_publish(
                {"user_id": user_id, "notify_user": True, "source": "internal_command"},
                "airdeliver.ai.cart.clear",
            )
            return

        if parsed.name == InternalCommand.CONFIRM_ORDER:
            await self._safe_publish(
                {
                    "user_id": user_id,
                    "type": "payment_intent",
                    "timestamp": _utc_timestamp(),
                    "source": "internal_command",
                },
                "airdeliver.ai.order.confirm",
            )
            return

        if parsed.name == InternalCommand.SAVE_FOR_LATER:
            logger.info("internal_save_for_later", extra={"user_id": user_id})
            await self._safe_publish(
                {"user_id": user_id, "notify_user": True, "source": "internal_command"},
                "airdeliver.ai.cart.save",
            )
            await self._safe_send_ui(
                user_id,
                {"type": "typing", "content": "Archiving your manifest..."},
            )
            return

        if parsed.name == InternalCommand.GET_INITIAL_SUGGESTIONS:
            # Fallback handling just in case the method exists dynamically or logic demands
            if hasattr(self, "_handle_initial_suggestions"):
                await self._handle_initial_suggestions(user_id)
            return

        if parsed.name == InternalCommand.RESET_SESSION:
            context_key_getter = getattr(self, "_get_context_key", None)
            seen_key_getter = getattr(self, "_get_seen_key", None)

            cache_keys: List[str] = []
            if callable(context_key_getter):
                cache_keys.append(context_key_getter(user_id))
            if callable(seen_key_getter):
                cache_keys.append(seen_key_getter(user_id))

            cache_keys.append(f"u:{user_id}:home_matrix_cache")

            for key in cache_keys:
                await self._safe_delete_cache_key(key)

            await self._safe_publish(
                {"user_id": user_id, "notify_user": False, "source": "internal_command"},
                "airdeliver.ai.cart.clear",
            )

            await self._safe_send_ui(
                user_id,
                {
                    "content": "Session and memory cleared. Starting fresh.",
                    "type": "system",
                },
            )
            return

    async def _handle_initial_suggestions(self, user_id: int) -> None:
        logger.info("matrix_generation_started", extra={"user_id": user_id})

        # 1. Telemetry & DNA Acquisition
        spending_tier = self.config.default_spending_tier
        global_seen_ids: Set[int] = set()

        if self.behavior_engine:
            try:
                if hasattr(self.behavior_engine, 'analyze_financial_dna'):
                    spending_tier = await self.behavior_engine.analyze_financial_dna(user_id)
                if hasattr(self.behavior_engine, 'get_recently_seen_ids'):
                    recent_ids = await self.behavior_engine.get_recently_seen_ids(user_id)
                    if recent_ids:
                        global_seen_ids.update(recent_ids)
            except Exception as e:
                logger.warning("behavior_engine_telemetry_degraded", extra={"user_id": user_id, "error": str(e)})

        # 2. Data Acquisition Pipeline (Sequential Execution for DB Safety)
        personal_products = await self._fetch_personal(user_id, global_seen_ids, spending_tier)
        self._register_seen(global_seen_ids, personal_products)

        bestsellers = await self._fetch_bestsellers(global_seen_ids)
        self._register_seen(global_seen_ids, bestsellers)

        trending = await self._fetch_trending(global_seen_ids)
        self._register_seen(global_seen_ids, trending)

        deals = await self._fetch_deals(global_seen_ids)
        self._register_seen(global_seen_ids, deals)

        # 3. Progressive Delivery Pipeline
        streamed_any = False

        if personal_products:
            await self._stream_row(
                user_id, self._get_time_aware_greeting(spending_tier), "proactive_suggestion",
                personal_products, "Exclusively curated to align with your distinct taste."
            )
            streamed_any = True

        if bestsellers:
            await self._stream_row(
                user_id, self.config.copy_bestsellers, "product_carousel",
                bestsellers, "Global Market Leaders"
            )
            streamed_any = True

        if trending:
            await self._stream_row(
                user_id, self.config.copy_trending, "product_carousel",
                trending, "High-Velocity Trending"
            )
            streamed_any = True

        if deals:
            await self._stream_row(
                user_id, self.config.copy_deals, "product_carousel",
                deals, "Optimal Price Point", apply_delay=False 
            )
            streamed_any = True

        if not streamed_any:
            await self._send_to_ui(user_id, {"content": self.config.copy_fallback, "type": "text"})

    # --- 🛠️ Matrix Helper Methods ---

    def _register_seen(self, memory_set: Set[int], products: Sequence[Product]) -> None:
        """يضيف المنتجات المسترجعة لقائمة الـ Seen لمنع تكرارها في الصفوف التالية"""
        for p in products:
            memory_set.add(p.id)

    async def _stream_row(self, user_id: int, content: str, ui_type: str, products: Sequence[Product], reason: str, apply_delay: bool = True) -> None:
        """تغليف عملية الإرسال للواجهة مع إضافة Delay لتأثير الـ Streaming"""
        try:
            payload = {
                "content": content,
                "type": ui_type,
                "products": [p.model_dump(mode='json') for p in products],
                "reason": reason
            }
            await self._send_to_ui(user_id, payload)
            if apply_delay:
                await asyncio.sleep(self.config.stream_delay_sec)
        except Exception as e:
            logger.error("stream_row_transport_failure", extra={"error": str(e)})

    async def _fetch_personal(self, user_id: int, seen_ids: Set[int], tier: str) -> Sequence[Product]:
        try:
            return await self.search_engine.get_fresh_homepage_matrix(self.db, user_id, list(seen_ids), tier)
        except Exception as e:
            logger.warning("fetch_personal_failed", extra={"error": str(e)})
            return []

    async def _fetch_bestsellers(self, seen_ids: Set[int]) -> Sequence[Product]:
        try:
            stmt = select(Product)
            
            if seen_ids: stmt = stmt.where(Product.id.notin_(seen_ids))
            # ✅ استخدام المتغير الصحيح من self.config
            stmt = stmt.order_by(col(Product.rating).desc()).limit(self.config.max_items_per_row)
            return (await self.db.execute(stmt)).scalars().all()
        except Exception as e:
            logger.warning("fetch_bestsellers_failed", extra={"error": str(e)})
            return []

    async def _fetch_trending(self, seen_ids: Set[int]) -> Sequence[Product]:
        try:
            stmt = select(Product)
            if seen_ids: stmt = stmt.where(Product.id.notin_(seen_ids))
            # ✅ استخدام المتغير الصحيح من self.config
            stmt = stmt.limit(self.config.trending_pool_limit)
            pool = list((await self.db.execute(stmt)).scalars().all())
            if not pool: return []
            return random.sample(pool, min(len(pool), self.config.max_items_per_row))
        except Exception as e:
            logger.warning("fetch_trending_failed", extra={"error": str(e)})
            return []

    async def _fetch_deals(self, seen_ids: Set[int]) -> Sequence[Product]:
        try:
            stmt = select(Product).where(Product.rating >= self.config.deals_min_rating)
            if seen_ids: stmt = stmt.where(Product.id.notin_(seen_ids))
            stmt = stmt.order_by(col(Product.price).asc()).limit(self.config.max_items_per_row)
            return (await self.db.execute(stmt)).scalars().all()
        except Exception as e:
            logger.warning("fetch_deals_failed", extra={"error": str(e)})
            return []
    # -------------------------------------------------------------------------
    # VISION / QUERY PLANNING
    # -------------------------------------------------------------------------

    async def _resolve_vision_query(self, request: IncomingMessage, ctx: RequestContext) -> Tuple[str, str]:
        if not request.image_b64:
            return request.message_text, ""

        try:
            search_query = await asyncio.wait_for(
                self.llm_service.analyze_product_image(request.image_b64),
                timeout=self.config.image_analysis_timeout_sec,
            )
            return search_query, f"Visual identification: {search_query}"
        except asyncio.TimeoutError:
            StructuredLog.error(
                "vision_timeout",
                correlation_id=ctx.correlation_id,
                user_id=request.user_id,
                timeout=self.config.image_analysis_timeout_sec,
            )
            return "trending high-tech items", ""
        except Exception as exc:
            StructuredLog.error(
                "vision_failure",
                correlation_id=ctx.correlation_id,
                user_id=request.user_id,
                error=str(exc),
            )
            return "trending high-tech items", ""

    async def _optimize_search_query(self, search_query: str) -> str:
        if len(search_query.split()) > 4 or "?" in search_query:
            try:
                optimized = await self.llm_service.extract_search_terms(search_query)
                return optimized or search_query
            except Exception:
                return search_query
        return search_query

    def _build_search_plan(
        self,
        *,
        optimized_query: str,
        original_message: str,
        vision_description: str,
        has_image: bool,
    ) -> SearchPlan:
        constraints = self._extract_neuro_constraints(optimized_query)
        broad_triggers = [
            "best", "recommend", "suggestion", "what is", "top", "trending",
            "collection", "show me", "افضل", "اقتراح", "ترشيح", "وريني",
        ]
        lower_text = original_message.lower()
        is_broad_query = any(trigger in lower_text for trigger in broad_triggers) and len(lower_text.split()) < 4
        is_specs_query = any(
            token in lower_text for token in ["specs", "specification", "technical", "مواصفات", "تفاصيل"]
        ) or has_image

        return SearchPlan(
            search_query=constraints.clean_query if constraints.clean_query else optimized_query,
            vision_description=vision_description,
            constraints=constraints,
            is_specs_query=is_specs_query,
            is_broad_query=is_broad_query,
        )

    def _extract_neuro_constraints(self, text: str) -> SearchConstraints:
        return self.constraint_extractor.extract(text)

    # -------------------------------------------------------------------------
    # SEARCH / RANK / FILTER (Including v3 Strategic Options)
    # -------------------------------------------------------------------------

    async def _execute_search(
        self,
        *,
        request: IncomingMessage,
        plan: SearchPlan,
        ctx: RequestContext,
    ) -> Tuple[List[ProductLike], bool, str]:
        candidates: List[ProductLike] = []
        fallback_trigger = False
        ai_response_prefix = ""

        if request.msg_type == MessageType.WELCOME_INTENT:
            search_vibe = self._normalize_welcome_search_vibe(request.message_text)
            candidates = await self.search_engine.perform_hybrid_search_pure(self.db, search_vibe, limit=4)
            if not candidates:
                candidates = await self.search_engine.perform_hybrid_search_pure(self.db, "Trending Collections")
            return list(candidates), fallback_trigger, ai_response_prefix

        filters = plan.constraints.to_filters()

        @dataclass
        class DynamicStrategy:
            search_queries: List[str]
            category_filter: Optional[str]

        strategy = DynamicStrategy(
            search_queries=[plan.search_query],
            category_filter=plan.constraints.category_filter
        )

        try:
            candidates = await asyncio.wait_for(
                self._execute_strategic_search(
                    strategy=strategy,
                    user_id=request.user_id,
                    original_query=plan.search_query
                ),
                timeout=self.config.search_timeout_sec,
            )

            if not candidates:
                candidates = await asyncio.wait_for(
                    self._find_smart_alternatives(
                        original_query=plan.search_query,
                        strategy=strategy
                    ),
                    timeout=self.config.search_timeout_sec,
                )
                if candidates:
                    fallback_trigger = True
                    ai_response_prefix = "I couldn't find an exact match, but here are the best smart alternatives: "

        except asyncio.TimeoutError:
            StructuredLog.warning(
                "search_timeout",
                correlation_id=ctx.correlation_id,
                user_id=request.user_id,
                query=plan.search_query,
            )
            return [], fallback_trigger, ai_response_prefix

        candidates = self.ranker.rerank(request.message_text, candidates)

        if plan.constraints.excluded_keywords and candidates:
            filtered: List[ProductLike] = []
            for prod in candidates:
                p_name = str(ProductAccess.get(prod, "name", ""))
                p_desc = str(ProductAccess.get(prod, "description", ""))
                p_cat = str(ProductAccess.get(prod, "category", ""))
                p_text = f"{p_name} {p_desc} {p_cat}".lower()
                if any(bad_word in p_text for bad_word in plan.constraints.excluded_keywords):
                    continue
                filtered.append(prod)
            candidates = filtered

        if plan.constraints.price_max and candidates:
            price_filtered = [
                p for p in candidates
                if float(ProductAccess.get(p, "price", 0) or 0) <= plan.constraints.price_max
            ]
        

            if not price_filtered:
                StructuredLog.info(
                    "search_constraints_relaxed",
                    correlation_id=ctx.correlation_id,
                    user_id=request.user_id,
                    query=plan.search_query,
                    price_max=plan.constraints.price_max,
                )
                fallback_trigger = True
                candidates = await self.search_engine.perform_hybrid_search_pure(self.db, plan.search_query, limit=5)
                ai_response_prefix = (
                    f"I couldn't find matches under ${plan.constraints.price_max}, "
                    "but here are the best options available: "
                )
            else:
                candidates = price_filtered

        return list(candidates), fallback_trigger, ai_response_prefix

    async def _execute_strategic_search(self, strategy: Any, user_id: int, original_query: str) -> List[Any]:
        """
        Executes a bounded multi-tier search strategy (from v3).
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        normalized_query = _normalize_search_text(original_query)
        if not normalized_query:
            return []

        search_queries = getattr(strategy, "search_queries", None) or []
        category_filter = getattr(strategy, "category_filter", None)

        core_query = _normalize_search_text(search_queries[0] if search_queries else normalized_query)
        strict_filters = {"category": category_filter} if category_filter else None

        logger.info(
            "strategic_search_started",
            extra={
                "user_id": user_id,
                "original_query": normalized_query,
                "core_query": core_query,
                "category_filter": category_filter,
            },
        )

        high_tier = await self.search_engine.perform_hybrid_search_pure(
            self.db,
            core_query,
            limit=30,
            filters=strict_filters,
        )

        exact_matches: List[Any] = []
        alternatives: List[Any] = []

        query_terms = {term for term in core_query.lower().split() if term}
        for product in high_tier:
            name_value = str(_safe_product_get(product, "name", "")).lower()
            if query_terms and all(term in name_value for term in query_terms):
                exact_matches.append(product)
            else:
                alternatives.append(product)

        if exact_matches:
            exact_matches.sort(
                key=lambda item: float(_safe_product_get(item, "price", 0) or 0),
                reverse=True,
            )
            result = _deduplicate_products(exact_matches[:5])
            logger.info(
                "strategic_search_tier_hit",
                extra={"user_id": user_id, "tier": "high_precision_exact", "count": len(result)},
            )
            return result

        if alternatives:
            ranked = self.ranker.rerank(core_query, alternatives)[:5]
            ranked = _deduplicate_products(ranked)
            logger.info(
                "strategic_search_tier_hit",
                extra={"user_id": user_id, "tier": "high_precision_ranked", "count": len(ranked)},
            )
            return ranked

        mid_tier = await self.search_engine.perform_hybrid_search_pure(
            self.db,
            core_query,
            limit=10,
            filters=strict_filters,
        )
        if mid_tier:
            ranked = self.ranker.rerank(core_query, mid_tier)[:5]
            ranked = _deduplicate_products(ranked)
            logger.info(
                "strategic_search_tier_hit",
                extra={"user_id": user_id, "tier": "mid_precision", "count": len(ranked)},
            )
            return ranked

        broad_query = " ".join(core_query.split()[:2]).strip() or core_query
        broad_results = await self.search_engine.perform_hybrid_search_pure(
            self.db,
            broad_query,
            limit=5,
        )
        broad_results = _deduplicate_products(broad_results)

        logger.info(
            "strategic_search_tier_hit",
            extra={"user_id": user_id, "tier": "broad_fallback", "count": len(broad_results), "broad_query": broad_query},
        )
        return broad_results

    async def _find_smart_alternatives(self, original_query: str, strategy: Any) -> List[Any]:
        """
        Finds bounded fallback alternatives when direct search fails (from v3).
        """
        normalized_query = _normalize_search_text(original_query)
        if not normalized_query:
            return []

        category_filter = getattr(strategy, "category_filter", None) if strategy is not None else None

        if category_filter:
            logger.info(
                "smart_alternatives_category_fallback",
                extra={"query": normalized_query, "category_filter": category_filter},
            )
            results = await self.search_engine.perform_hybrid_search_pure(
                self.db,
                normalized_query,
                limit=5,
                filters={"category": category_filter},
            )
            return _deduplicate_products(results)

        clean_query = re.sub(
            r"\b(specs|price|buy|best|review|of)\b",
            " ",
            normalized_query,
            flags=re.IGNORECASE,
        )
        clean_query = re.sub(r"\s+", " ", clean_query).strip() or normalized_query

        logger.info(
            "smart_alternatives_generic_fallback",
            extra={"original_query": normalized_query, "clean_query": clean_query},
        )
        results = await self.search_engine.perform_hybrid_search_pure(
            self.db,
            clean_query,
            limit=5,
        )
        return _deduplicate_products(results)

    def _normalize_welcome_search_vibe(self, search_vibe: str) -> str:
        system_artifacts = [
            "User just connected.", "IGNORE 'Hello'.", "Start immediately.",
            "Direct approach.", "Skip greetings.", "Act excited.",
            "New session.", "Connection active.", "Jump straight into",
            "Be intriguing", "Be provocative",
        ]
        clean = search_vibe
        for artifact in system_artifacts:
            clean = clean.replace(artifact, "")
        clean = clean.strip().strip(".,'\"")
        return clean or "Titanium & High-End Tech"

    def _finalize_candidates(
        self,
        *,
        message_text: str,
        lower_text: str,
        has_image: bool,
        candidates: Sequence[ProductLike],
    ) -> List[ProductLike]:
        final_products = list(candidates[: self.config.max_final_products])

        if final_products and not has_image:
            is_broad_query = any(
                token in lower_text
                for token in ["best", "recommend", "suggestion", "what is", "top", "trending", "collection", "show me", "افضل", "اقتراح", "ترشيح", "وريني"]
            ) and len(lower_text.split()) < 4

            if not is_broad_query:
                top_candidate = final_products[0]
                match_ratio = self.interceptor.validate_alignment(user_query=message_text, top_candidate=top_candidate)

                if match_ratio < self.interceptor.matcher_threshold:
                    strategic_alternatives = []
                    try:
                        strategic_alternatives = asyncio.get_event_loop()
                    except Exception:
                        pass

        return final_products

    # -------------------------------------------------------------------------
    # RESPONSE SYNTHESIS
    # -------------------------------------------------------------------------

    async def _synthesize_response(
        self,
        *,
        request: IncomingMessage,
        ctx: RequestContext,
        plan: SearchPlan,
        final_products: Sequence[ProductLike],
        ai_response_prefix: str,
    ) -> LlmDecision:
        products = list(final_products)
        ai_response_text = ""
        recovery_mode = False

        if products and not request.image_b64:
            top_product = products[0]
            product_payload = ProductAccess.dump(top_product)

            if plan.is_specs_query:
                try:
                    ai_response_text = await self.llm_service.consult_on_product(
                        product_data=product_payload,
                        question=request.message_text,
                    )
                except Exception as exc:
                    StructuredLog.warning(
                        "consult_on_product_failed",
                        correlation_id=ctx.correlation_id,
                        user_id=request.user_id,
                        error=str(exc),
                    )
                    ai_response_text = f"Check out {ProductAccess.get(top_product, 'name', 'this item')}, it matches what you are looking for."
            else:
                try:
                    chat_context = await self._get_conversation_context(request.user_id)
                    ai_response_text = await self._generate_genius_response(
                        user_id=request.user_id,
                        user_query=request.message_text,
                        product=top_product,
                        chat_history=chat_context,
                    )
                except Exception as exc:
                    StructuredLog.warning(
                        "genius_response_failed",
                        correlation_id=ctx.correlation_id,
                        user_id=request.user_id,
                        error=str(exc),
                    )
                    ai_response_text = f"Check out {ProductAccess.get(top_product, 'name', 'this item')}, it matches what you are looking for."

            if ai_response_prefix:
                ai_response_text = f"{ai_response_prefix}{ai_response_text}"

            return LlmDecision(
                response_text=ai_response_text,
                products=tuple(products),
                response_type=UiPayloadType.PRODUCT_CAROUSEL,
                reason="Selected as the optimal matches proven to deliver the highest caliber of user satisfaction and performance.",
            )

        if not products or plan.is_specs_query or request.image_b64:
            try:
                if not products:
                    recovery_mode = True
                    products = await self._perform_smart_recovery(plan.search_query)

                alternative_context = ""
                p_name_override = ""

                if products:
                    top_product = products[0]
                    p_name_override = str(ProductAccess.get(top_product, "name", ""))
                    p_desc = str(ProductAccess.get(top_product, "description", ""))[: self.config.max_product_desc_chars]
                    p_price = ProductAccess.get(top_product, "price", "")
                    alternative_context = (
                        f"WE HAVE THIS IN STOCK: {p_name_override} (Price: ${p_price}). Specs: {p_desc}"
                    )

                web_intel = await asyncio.wait_for(
                    self.llm_service._perform_web_search(plan.search_query),
                    timeout=self.config.web_search_timeout_sec,
                )
                web_intel_safe = str(web_intel)[: self.config.max_web_context_chars]

                system_instruction = """
                  ROLE: airdeliver Elite Personal Shopping Concierge.

                  PERSONA & TONE:
                  You speak with the calm, refined authority of a world-class luxury advisor. Your tone is elegant, composed, and effortlessly helpful. You never apologize excessively or use cheap sales pressure. You turn unavailability into an opportunity for discovery.

                  MISSION:
                  The user's requested item is out of stock. You must inform them gracefully and present the system's suggested alternative with intelligent framing and flawless visual formatting.

                  EXECUTION STRATEGY:
                  1. The Elegant Truth: State briefly and politely that the requested item is currently unavailable. One sentence only. Do not dwell on the negative.
                  2. The Intelligent Pivot (Crucial):
                  - DIRECT MATCH (e.g., watch to watch): If the alternative is in the same category, transition smoothly by explaining why this specific alternative is a brilliant, logical choice.
                  - LIFESTYLE LEAP (e.g., watch to drone): If the alternative is in a completely different category, DO NOT pretend it is a substitute. Acknowledge the shift immediately. Pivot using their implied taste. Example: "While that piece is unavailable, knowing your appreciation for flagship tech and premium engineering, I curated this for you..."
                  3. The Value Presentation: Explain the suggested item in one short, persuasive paragraph highlighting its real-world value.

                  VISUAL & FORMATTING DISCIPLINE:
                  - Write for a narrow, premium chat bubble. Use short sentences.
                  - Separate paragraphs with a single blank line.
                  - Feature exactly 2 to 3 key highlights using ONLY this specific bullet symbol: ●
                  - FORBIDDEN: Zero markdown headings (no #). Zero dashes (-). Zero asterisks (*). Zero bold/italic markdown.
                  - End with one calm, confident closing sentence. Never use aggressive urgency like "Order now" or "Fastest delivery".
                  """

                user_payload = (
                    "USER REQUEST:\n"
                    f"{request.message_text}\n\n"
                    "MATCH STATUS:\n"
                    "The exact requested item is unavailable.\n\n"
                    "AVAILABLE ALTERNATIVE:\n"
                    f"{alternative_context}\n\n"
                    "TASK:\n"
                    "Respond as an elite shopping concierge.\n"
                    "If the available item is a true logical alternative, present it as a refined recommendation.\n"
                    "If it belongs to a different category, do not frame it as a direct substitute.\n"
                    "Instead, pivot intelligently based on the user's taste, intent, and likely preference profile.\n"
                    "Keep the response visually elegant, persuasive, and easy to read inside a premium chat interface."
                )

                context_payload = (
                    "SUPPORTING INTELLIGENCE\n\n"
                    f"VISUAL ANALYSIS:\n{plan.vision_description or 'No visual analysis available.'}\n\n"
                    f"WEB INTEL:\n{web_intel_safe or 'No external market intelligence available.'}"
                )

                ai_response_text = await self.llm_service.generate_response(
                    prompt=user_payload,
                    system_role=system_instruction,
                    context=context_payload,
                    max_tokens=2500,
                    temperature=0.35,
                )

            except Exception as exc:
                StructuredLog.error(
                    "deep_research_failure",
                    correlation_id=ctx.correlation_id,
                    user_id=request.user_id,
                    error=str(exc),
                )
                if products:
                    ai_response_text = (
                        f"The exact item isn't available, but I highly recommend "
                        f"{ProductAccess.get(products[0], 'name', 'this option')}. "
                        "It's the best alternative in our collection."
                    )
                else:
                    ai_response_text = "I'm checking our live inventory global warehouses. Please wait a moment."

            return LlmDecision(
                response_text=ai_response_text,
                products=tuple(products),
                response_type=UiPayloadType.PRODUCT_CAROUSEL if products else UiPayloadType.TEXT,
                reason="Selected as the optimal matches proven to deliver the highest caliber of user satisfaction and performance.",
            )

        if request.msg_type == MessageType.WELCOME_INTENT:
            ai_response_text = "Welcome! I'm your Global Shopping Intelligence. Send me a photo or a request to begin."
        else:
            ai_response_text = "I've checked our global inventory, but that item isn't ready for delivery. How else can I assist?"

        return LlmDecision(
            response_text=ai_response_text,
            products=tuple(products),
            response_type=UiPayloadType.TEXT,
            reason="Selected as the optimal matches proven to deliver the highest caliber of user satisfaction and performance.",
        )

    # -------------------------------------------------------------------------
    # RECOVERY / COMMANDS / TELEMETRY
    # -------------------------------------------------------------------------

    async def _perform_smart_recovery(self, user_query: str) -> List[ProductLike]:
        try:
            system_instruction = (
                "You are a Universal Category Strategist. "
                "Analyze the missing item and output strictly: "
                "'Broad_Category_Name | Complement_1_Keyword Complement_2_Keyword'. "
                "Adapt to the category, do not assume tech."
            )

            llm_analysis = await self.llm_service.generate_response(
                prompt=f"Missing Item: {user_query}",
                system_role=system_instruction,
                temperature=0.1,
                max_tokens=2500,
            )

            llm_analysis = llm_analysis.strip().replace('"', "").replace("'", "")

            if "|" in llm_analysis:
                parts = llm_analysis.split("|", 1)
                parent_category = parts[0].strip()
                complements_keywords = parts[1].strip()
            else:
                parent_category = self._distill_fallback_parent_category(user_query)
                complements_keywords = "Best Sellers"

            found_alternatives = await self.search_engine.perform_hybrid_search_pure(self.db, parent_category, limit=5)
            found_complements = await self.search_engine.perform_hybrid_search_pure(self.db, complements_keywords, limit=3)

            final_mix: List[ProductLike] = []
            seen_ids: Set[Any] = set()

            for product in found_alternatives[:2]:
                product_id = ProductAccess.get(product, "id", None)
                if product_id not in seen_ids:
                    final_mix.append(product)
                    seen_ids.add(product_id)

            for product in found_complements[:1]:
                product_id = ProductAccess.get(product, "id", None)
                if product_id not in seen_ids:
                    final_mix.append(product)
                    seen_ids.add(product_id)

            if len(final_mix) < self.config.max_recovery_products:
                for product in found_alternatives[2:5]:
                    product_id = ProductAccess.get(product, "id", None)
                    if product_id not in seen_ids:
                        final_mix.append(product)
                        seen_ids.add(product_id)
                        if len(final_mix) >= self.config.max_recovery_products:
                            break

            return final_mix

        except Exception as exc:
            StructuredLog.error("smart_recovery_failed", error=str(exc))
            safe_fallback = (user_query.split()[0] if user_query else "Trending")[: self.config.max_safe_fallback_query_chars]
            return await self.search_engine.perform_hybrid_search_pure(self.db, safe_fallback, limit=3)

    def _distill_fallback_parent_category(self, user_query: str) -> str:
        noise_words = {
            "i", "me", "my", "we", "want", "need", "looking", "look", "for", "search", "find",
            "can", "could", "would", "is", "are", "am", "was", "be", "have", "has", "do", "does",
            "a", "an", "the", "in", "on", "at", "with", "without", "and", "or", "but", "so",
            "please", "hello", "hi", "hey", "dear", "sir", "madam", "recommend", "suggest",
            "best", "top", "good", "great", "cheap", "expensive", "new", "latest", "review",
            "انا", "عايز", "عاوز", "محتاج", "بدي", "ابغى", "ابي", "ادور", "ابحث", "لو", "سمحت",
            "ممكن", "من", "فضلك", "بالله", "عن", "مع", "في", "على", "الي", "اللي", "ده", "دي",
            "افضل", "احسن", "ارخص", "اغلى", "اجدد", "اقوى", "ترشيح", "اقتراح", "ساعدني", "وريني",
            "شو", "شنو", "ايش", "هل", "فيه", "عندك", "موجود", "بكام", "سعر",
        }

        clean_text = re.sub(r"[^\w\s]", "", user_query.lower())
        words = clean_text.split()
        core_keywords = [w for w in words if w not in noise_words and len(w) > 1]
        if core_keywords:
            return " ".join(core_keywords[:4])
        return user_query[: self.config.max_safe_fallback_query_chars]

    async def _handle_text_commands(self, user_id: int, text: str, full_payload: dict) -> bool:
        """
        Enterprise-grade semantic command interceptor (from v3).
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        normalized_text = _sanitize_free_text(text)
        if not normalized_text:
            return False

        checkout_triggers = ("checkout", "pay now", "confirm order", "finish order", "دفع")
        clear_cart_triggers = ("clear cart", "empty cart", "delete cart", "مسح السلة")
        add_triggers = (
            "add to cart", "put in cart", "add this", 
            "ضيف للسلة", "حطه في السلة", "اضف الى السلة", "ضيفه للسلة"
        )
        reset_triggers = ("reset", "restart", "help")

        if _contains_any(normalized_text, checkout_triggers):
            logger.info(
                "text_command_checkout_detected",
                extra={"user_id": user_id, "command_text": normalized_text},
            )
            await self._safe_publish(
                {
                    "user_id": user_id,
                    "type": "payment_intent",
                    "timestamp": _utc_timestamp(),
                    "source": "nlu_text_command",
                },
                "airdeliver.ai.order.confirm",
            )
            return True

        if _contains_any(normalized_text, clear_cart_triggers):
            logger.info(
                "text_command_clear_cart_detected",
                extra={"user_id": user_id, "command_text": normalized_text},
            )
            await self._safe_publish(
                {
                    "user_id": user_id,
                    "notify_user": True,
                    "source": "nlu_text_command",
                },
                "airdeliver.ai.cart.clear",
            )
            return True

        if normalized_text in reset_triggers:
            logger.info(
                "text_command_reset_detected",
                extra={"user_id": user_id, "command_text": normalized_text},
            )
            await self._process_internal_command(user_id, InternalCommand.RESET_SESSION.value)
            return True

        if _contains_any(normalized_text, add_triggers):
            query_product = _strip_trigger_prefixes(normalized_text, add_triggers)

            if len(query_product) <= 2:
                logger.info(
                    "text_command_add_skipped_query_too_short",
                    extra={"user_id": user_id, "command_text": normalized_text},
                )
                return False

            try:
                candidates = await self._search_single_product(query_product, limit=1)
            except Exception as exc:
                logger.error(
                    "text_command_add_search_failed",
                    extra={"user_id": user_id, "query_product": query_product, "error": str(exc)},
                )
                return False

            if not candidates:
                logger.info(
                    "text_command_add_no_candidate_found",
                    extra={"user_id": user_id, "query_product": query_product},
                )
                return False

            target = candidates[0]
            target_id = _safe_product_get(target, "id", None)
            target_name = str(_safe_product_get(target, "name", "item"))

            if target_id is None:
                logger.error(
                    "text_command_add_candidate_missing_id",
                    extra={"user_id": user_id, "query_product": query_product, "target_name": target_name},
                )
                return False

            await self._safe_publish(
                {
                    "user_id": user_id,
                    "product_id": target_id,
                    "quantity": 1,
                    "notify_user": False,
                    "source": "nlu_text_command",
                },
                "airdeliver.ai.cart.add",
            )

            bundle = await self._safe_bundle_generation(target)
            bundle = _deduplicate_products(bundle)

            ui_message = f"Added {target_name} to cart."
            reason = "Cart Action"
            products_payload: List[Dict[str, Any]] = []

            if bundle:
                ui_message += "\n\nSmart suggestion: Complete the set with these related items."
                reason = "Cart + Bundle"
                products_payload = [_safe_product_dump(item) for item in bundle]

            await self._safe_send_ui(
                user_id,
                {
                    "content": ui_message,
                    "type": "product_carousel",
                    "products": products_payload,
                    "reason": reason,
                },
            )
            return True

        return False

    async def _bg_memorize(self, user_id: int, text: str) -> None:
        """
        Best-effort async memory extraction hook (from v3).
        """
        if not isinstance(user_id, int) or user_id <= 0:
            return

        normalized_text = _normalize_search_text(text)
        if not normalized_text:
            return

        try:
            extractor = getattr(self.llm_service, "extract_memory_worthy_facts", None)
            if extractor is None or not callable(extractor):
                logger.debug(
                    "bg_memorize_skipped_extractor_unavailable",
                    extra={"user_id": user_id},
                )
                return

            fact = await extractor(normalized_text)
            if not fact:
                logger.debug(
                    "bg_memorize_no_fact_extracted",
                    extra={"user_id": user_id},
                )
                return

            logger.info(
                "bg_memorize_fact_extracted",
                extra={"user_id": user_id, "fact_preview": str(fact)[:200]},
            )

            persistence_hook = getattr(self.search_engine, "remember", None)
            if persistence_hook is not None and callable(persistence_hook):
                try:
                    await persistence_hook(user_id=user_id, fact=fact)
                    logger.info(
                        "bg_memorize_fact_persisted",
                        extra={"user_id": user_id},
                    )
                    return
                except Exception as exc:
                    logger.warning(
                        "bg_memorize_engine_persist_failed",
                        extra={"user_id": user_id, "error": str(exc)},
                    )

            logger.debug(
                "bg_memorize_persistence_not_supported",
                extra={"user_id": user_id},
            )

        except Exception as exc:
            logger.warning(
                "bg_memorize_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )

    async def _mark_products_as_seen(self, user_id: int, products: Sequence[ProductLike]) -> None:
        if not products:
            return
        try:
            key = RedisKeys.seen_products(user_id)
            ids: List[str] = []
            for product in products:
                value = ProductAccess.get(product, "id", None)
                if value is not None:
                    ids.append(str(value))
            if ids:
                await self.cache.sadd(key, *ids)
                await self.cache.expire(key, self.config.seen_cache_ttl_sec)
        except Exception as exc:
            StructuredLog.warning("mark_products_seen_failed", user_id=user_id, error=str(exc))

    async def _update_implicit_memory(self, user_id: int, products: Sequence[ProductLike], action: str = "view") -> None:
        if not self.behavior_engine or not products:
            return
        try:
            tags: List[str] = []
            for product in products:
                category = ProductAccess.get(product, "category", "")
                name = ProductAccess.get(product, "name", "")
                if category or name:
                    tags.append(f"{category} {name}".strip())

            if tags and hasattr(self.behavior_engine, "register_interaction"):
                signal = " ".join(tags)
                weight = 2.0 if action == "search_hit" else 1.0
                await self.behavior_engine.register_interaction(user_id, signal, weight=weight)
        except Exception as exc:
            StructuredLog.warning("implicit_memory_update_failed", user_id=user_id, error=str(exc))

    async def _try_route_welcome_matrix(self, request: IncomingMessage, ctx: RequestContext) -> bool:
        matrix_data = request.raw_payload.get("data", {})
        if isinstance(matrix_data, Mapping) and "matrix_cards" in matrix_data:
            await self._send_to_ui(
                request.user_id,
                {
                    "type": UiPayloadType.LIFESTYLE_MATRIX.value,
                    "content": matrix_data.get("header_text", "Select your lifestyle archetype:"),
                    "matrix": matrix_data["matrix_cards"],
                    "reason": "Direct Context Injection",
                },
                ctx,
            )
            return True
        return False

    # -------------------------------------------------------------------------
    # COPY / GENERATION
    # -------------------------------------------------------------------------

    def _get_time_context(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        if 12 <= hour < 17:
            return "afternoon"
        if 17 <= hour < 22:
            return "evening"
        return "night"

    def _get_time_aware_greeting(self, tier: str = "MEDIUM") -> str:
        hour = datetime.now().hour
        if tier == "HIGH":
            prefix = "Curated premium picks"
        elif tier == "LOW":
            prefix = "Strong value picks"
        else:
            prefix = "Relevant picks"

        if 5 <= hour < 12:
            return f"Good morning. {prefix} for your current search."
        if 12 <= hour < 18:
            return f"Good afternoon. {prefix} for your current search."
        if 18 <= hour < 22:
            return f"Good evening. {prefix} for your current search."
        return f"{prefix} for your current search."

    async def _generate_dynamic_copy(self, user_id: int, tone: str, product: ProductLike, context: str = "") -> str:
        time_ctx = self._get_time_context()
        p_name = str(ProductAccess.get(product, "name", "this item"))

        if tone == "nudge":
            return random.choice(
                [
                    f"Still thinking about {p_name}?",
                    f"Don't miss out on {p_name}. Stock is moving fast.",
                    f"Quick heads up: {p_name} is trending right now.",
                ]
            )

        if tone == "welcoming":
            return self._get_time_aware_greeting("MEDIUM")

        templates = {
            "morning": [f"Start your day with {p_name}.", f"Morning essential: {p_name}."],
            "afternoon": [f"Boost your afternoon with {p_name}.", f"Have you seen this? {p_name}."],
            "evening": [f"Relax with {p_name}.", f"Good evening. How about {p_name}?"],
            "night": [f"Late night find: {p_name}.", f"Perfect for the night: {p_name}."],
        }
        return random.choice(templates.get(time_ctx, templates["morning"]))

    async def _generate_genius_response(
        self,
        user_id: int,
        user_query: str,
        product: ProductLike,
        chat_history: str = "",
    ) -> str:
        user_profile = await self._get_user_dna(user_id)
        persona = user_profile.persona
        tier = user_profile.tier

        product_data = ProductAccess.dump(product)
        p_name = str(product_data.get("name", "this product"))
        p_price = product_data.get("price", "")

        word_limit = "500"
        style_guide = "Direct and helpful."
        strategy_instruction = "Focus on the value proposition."
        web_context = ""
        is_unknown_product = False

        generic_triggers = ["best", "recommend", "suggestion", "top", "good", "buy", "option", "review", "what is"]
        is_generic_query = any(trigger in user_query.lower() for trigger in generic_triggers)

        query_numbers = re.findall(r"\d+", user_query)
        major_version_mismatch = False
        if query_numbers:
            relevant_nums = [n for n in query_numbers if int(n) > 10]
            major_version_mismatch = any(num not in p_name for num in relevant_nums)

        keywords = [w for w in user_query.lower().split() if len(w) > 3]
        match_score = sum(1 for word in keywords if word in p_name.lower()) / len(keywords) if keywords else 1.0

        reasoning_triggers = ["should i", "switch", "vs", "compare", "better", "worth", "opinion", "difference", "thoughts", "advice", "review"]
        is_reasoning_query = any(token in user_query.lower() for token in reasoning_triggers)

        should_trigger_web = False
        if major_version_mismatch:
            should_trigger_web = True
        elif is_reasoning_query:
            should_trigger_web = False
        elif not is_generic_query and match_score < 0.4:
            should_trigger_web = True

        if should_trigger_web:
            is_unknown_product = True
            search_optimized = user_query[:300]
            try:
                web_context = await self.llm_service._perform_web_search(search_optimized)
            except Exception:
                web_context = ""
        else:
            is_unknown_product = False

        meta_analysis: Dict[str, Any] = {"stance": "AUTHORITATIVE", "uncertainty": 0.0}
        current_vector = None

        try:
            ghost_json = await self.cache.get_json(RedisKeys.ghost_profile(user_id))
            embedding_provider = getattr(self.search_engine, "get_query_embedding", None)

            if callable(embedding_provider):
                current_vector = await asyncio.wait_for(
                    embedding_provider(user_query),
                    timeout=self.config.embedding_timeout_sec,
                )
                if ghost_json is not None and current_vector is not None:
                    meta_analysis = self.meta_cognition.evaluate_confidence(ghost_json, current_vector)
        except asyncio.TimeoutError:
            StructuredLog.warning("meta_cognition_timeout", user_id=user_id)
        except Exception as exc:
            StructuredLog.warning("meta_cognition_failure", user_id=user_id, error=str(exc))

        stance = str(meta_analysis.get("stance", "AUTHORITATIVE"))
        is_comparison = any(w in user_query.lower() for w in ["vs", "compare", "better", "difference", "or", "مقارنة", "الفرق", "أحسن"])

        current_date_str = datetime.now().strftime("%B %d, %Y")
        if is_unknown_product:
            word_limit = "500"
            style_guide = "Sophisticated, expert, conversational, knowledgeable, up-to-date."
            strategy_instruction = f"""
TODAY'S DATE: {current_date_str}
Use web data when discussing the external product.
If web data indicates the product is released, use present tense.
If unreleased, use cautious speculative language.
After the external product discussion, pivot smoothly to the in-stock alternative.
Max word count: {word_limit}
"""
            stance = "INQUISITIVE"

        elif stance == "AUTHORITATIVE":
            discovery_triggers = [
                "best", "top", "recommend", "suggest", "advice", "guide",
                "review", "what", "which", "option", "choice", "selection",
                "vs", "compare", "difference", "better", "worse",
                "cheap", "budget", "expensive", "cost", "price", "deal", "offer",
                "latest", "new", "trend", "popular", "hot",
                "suitable", "perfect for", "good for", "looking for", "help",
            ]
            is_discovery_intent = any(trigger in user_query.lower() for trigger in discovery_triggers)

            p_name_lower = p_name.lower()
            q_lower = user_query.lower()
            is_different_product = False

            if not is_discovery_intent:
                universal_stopwords = [
                    "want", "need", "buy", "purchase", "get", "find", "search", "looking", "order",
                    "show", "me", "give", "suggest", "recommend", "advice", "help",
                    "price", "cost", "how", "much", "many", "cheap", "expensive", "deal", "offer",
                    "best", "top", "good", "great", "bad", "new", "latest", "trending",
                    "available", "stock", "in", "out", "ready",
                    "the", "a", "an", "is", "are", "can", "will", "do", "does",
                    "with", "without", "for", "from", "at", "on", "by", "and", "or",
                    "color", "size", "weight", "please", "hello", "hi", "hey",
                ]
                query_tokens = [w for w in q_lower.split() if w not in universal_stopwords and len(w) > 2]
                missing_keywords = [token for token in query_tokens if token not in p_name_lower]
                if missing_keywords and query_tokens and (len(missing_keywords) / len(query_tokens) > 0.3):
                    is_different_product = True

            if is_different_product:
                word_limit = "500"
                style_guide = "Honest, helpful, pivot-master."
                strategy_instruction = f"""
The user asks for '{user_query}', but we only have '{p_name}' in stock.
Admit the exact item is unavailable.
Immediately present {p_name} as the closest strong alternative.
Explain why it is a good choice in this category.
"""
            elif is_discovery_intent:
                word_limit = "500"
                style_guide = "Expert, advisory, solution-oriented."
                strategy_instruction = f"""
The user asked a discovery question: '{user_query}'.
Present {p_name} as the top recommendation.
Highlight two attributes that map directly to the user's intent.
End with a confident recommendation.
"""
            else:
                if is_comparison:
                    word_limit = "500"
                    style_guide = "Persuasive, comparative, product-focused."
                    strategy_instruction = f"""
The user is comparing alternatives.
You are selling {p_name}.
Acknowledge the competitor briefly, but position {p_name} as the better fit for the user's priority.
Highlight two strong specs or category strengths of {p_name}.
"""
                else:
                    style_guide = "Direct, punchy, decision-oriented."
                    if "Impulsive" in persona:
                        strategy_instruction = "Focus on speed, urgency, and fear of missing out."
                    elif tier == "HIGH":
                        strategy_instruction = "Focus on status, premium quality, and exclusivity."
                    elif tier == "LOW":
                        strategy_instruction = "Focus on value, savings, and efficiency."
                    else:
                        strategy_instruction = "Focus on the one big reason to buy. No fluff."

        elif stance == "ADAPTIVE_SHOCK":
            word_limit = "500"
            style_guide = "Reassuring, explanatory, bridge-building."
            strategy_instruction = "Acknowledge the shift in taste and explain why this product fits the new context."
        else:
            word_limit = "500"
            style_guide = "Educational, humble, collaborative."
            strategy_instruction = "Teach the user about the feature, then guide the decision."

        specs_context = json.dumps(
            {k: v for k, v in product_data.items() if k in ["name", "price", "brand", "rating"]},
            default=str,
        )

        rebuttal_triggers = ["why", "but", "doesn't", "don't", "no", "wrong", "false", "wait", "actually", "only"]
        is_rebuttal = any(trigger in user_query.lower() for trigger in rebuttal_triggers)

        if is_rebuttal:
           response_structure = """
Start with one calm sentence that acknowledges the user's concern clearly and respectfully.

Then write 2 to 3 short explanatory paragraphs with one blank line between them.
The first paragraph should explain the concern honestly.
The second paragraph should clarify the trade-off in practical terms.
The third paragraph should reframe the product around its strongest real-world advantage.

If there are specific strengths worth highlighting, place each one on its own separate line.
Use a bullet point for each strength so the response feels clean, structured, and easy to scan.

Formatting rules:
- Do not write the whole response as one continuous block.
- Use natural paragraph spacing.
- Keep paragraphs short and visually balanced.
- Put important advantages or reassurance points on separate bullet lines.
- Make the layout feel premium, calm, and well organized inside a chat bubble.

Tone rules:
- Sound confident, composed, and fair.
- Do not sound defensive.
- Do not dismiss the concern.
- Do not overhype the product.
- Persuade through clarity, balance, and trust.

Ending rule:
End with one short closing sentence that reinforces confidence without pressure.

Forbidden:
- Do not use the phrase "Order your product today for fastest delivery."
- Do not use aggressive sales pressure.
- Do not use cheap urgency language.
- Do not use markdown headings.
- Do not use quotes.
"""
        else:
            response_structure = """
Start with one direct opening sentence.

If you mention features, benefits, or important product points, you MUST use the thick bullet point symbol "●" for each item.
Do not use dashes (-) or numbers.

Keep each bullet concise and meaningful.
End with one calm, confident closing sentence.
"""

        system_prompt = f"""
You are the Ultimate Category Strategist.

Context:
- Target profile: {persona} [Financial Power: {tier}]
- User intent: {user_query}
- Candidate solution: {p_name} [Cost: {p_price}]
- Item attributes: {specs_context}
- Chat history: {chat_history[:1200]}
- Web intel: {str(web_context)[:1500]}

Mission:
{strategy_instruction}

Rules:
- Style: {style_guide}
- Max word count: {word_limit}
- If product and intent do not match, answer honestly and avoid pretending they match.
- No robotic apologies.
- No markdown.
- No quoted labels.
- Keep the response sharp, specific, and category-aware.

Structure:
{response_structure}
"""

        try:
            response = await self.llm_service.generate_response(
                prompt=f"User asked: '{user_query}'. Product: {p_name}. Execute strategy.",
                system_role=system_prompt,
                temperature=0.3,
                max_tokens=2500,
            )
            return str(response).strip().replace('"', "")
        except Exception as exc:
            StructuredLog.error("genius_generation_failed", user_id=user_id, error=str(exc))
            return f"Check out {p_name}, it matches your needs well. Current price: {p_price}."

    # -------------------------------------------------------------------------
    # OPTIONAL RECOVERY FLOW
    # -------------------------------------------------------------------------

    async def _perform_devilish_recovery(self, user_id: int, removed_pid: int) -> None:
        try:
            target = await self.db.get(Product, removed_pid)
            if not target:
                return

            raw_brand = getattr(target, "brand", None) or target.name.split()[0]
            base_price = float(target.price)
            category_core = target.category if getattr(target, "category", None) else target.name.split()[-1]

            devil_query = f"{raw_brand} {category_core} Flagship Pro Ultra Max Edition Premium"
            devil_filters: Dict[str, Any] = {
                "excluded_ids": [removed_pid],
                "price_min": base_price,
                "price_max": base_price * 4.0,
            }

            if getattr(target, "category", None):
                devil_filters["category"] = target.category

            candidates = await self.search_engine.perform_hybrid_search_pure(
                self.db,
                devil_query,
                limit=15,
                filters=devil_filters,
            )

            valid_upsells: List[ProductLike] = []
            for product in candidates:
                same_brand = raw_brand.lower() in str(ProductAccess.get(product, "name", "")).lower()
                product_rating = ProductAccess.get(product, "rating", None)
                target_rating = getattr(target, "rating", None)
                better_rating = (
                    product_rating is not None and target_rating is not None and product_rating >= target_rating
                )
                if same_brand or better_rating:
                    valid_upsells.append(product)

            valid_upsells.sort(key=lambda x: float(ProductAccess.get(x, "price", 0) or 0), reverse=True)
            final_selection = valid_upsells[:2]

            if final_selection:
                new_item_price = float(ProductAccess.get(final_selection[0], "price", 0) or 0)
                price_diff = new_item_price - base_price

                if price_diff > (base_price * 0.5):
                    headline = f"I noticed you removed {target.name}. Here are stronger premium alternatives."
                elif price_diff > 0:
                    headline = f"I noticed you removed {target.name}. Here are upgraded alternatives close to your range."
                else:
                    headline = f"I noticed you removed {target.name}. Here are top-rated alternatives."

                await self._send_to_ui(
                    user_id,
                    {
                        "content": headline,
                        "type": UiPayloadType.PRODUCT_CAROUSEL.value,
                        "products": [ProductAccess.dump(p) for p in final_selection],
                        "reason": "A superior tier of performance, engineered to surpass the limitations of your previous selection.",
                    },
                    RequestContext(user_id=user_id, correlation_id=f"recovery:{user_id}:{removed_pid}", received_at=time.monotonic()),
                )

                await asyncio.sleep(0.5)

                cart = await self.cache.get_json(RedisKeys.cart(user_id))
                if cart and cart.get("items"):
                    await self._send_to_ui(
                        user_id,
                        {
                            "content": None,
                            "type": UiPayloadType.CONFIRMATION_PROMPT.value,
                            "options": ["Confirm Order"],
                        },
                        RequestContext(user_id=user_id, correlation_id=f"confirm:{user_id}:{removed_pid}", received_at=time.monotonic()),
                    )

        except Exception as exc:
            StructuredLog.error("devilish_recovery_failed", user_id=user_id, removed_pid=removed_pid, error=str(exc))


# =============================================================================
# OPTIONAL FACTORY
# =============================================================================

def build_ai_nlu_service(
    db: AsyncSession,
    search_engine: AICommerceEngine,
    rabbitmq: RabbitMQService,
    cache: IAsyncCacheClient,
    llm_service: FreeLLMService,
    behavior_engine: Optional[BehaviorEngine] = None,
) -> AINLUService:
    return AINLUService(
        db=db,
        search_engine=search_engine,
        rabbitmq=rabbitmq,
        cache=cache,
        llm_service=llm_service,
        behavior_engine=behavior_engine,
    )
