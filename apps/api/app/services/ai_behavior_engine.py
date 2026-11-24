# apps/api/app/services/ai_behavior_engine.py

import asyncio
import base64
import json
import hashlib
import logging
import math
import re
import struct
import time
import uuid
from enum import Enum
from typing import List, Dict, Optional, Any, Set, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, Field, ValidationError, model_validator, ConfigDict

from app.services.cache_service import IAsyncCacheClient
from app.core.config import get_core_settings
from app.services.behavior_checkpoint import ModelArtifactError, load_behavior_checkpoint

logger = logging.getLogger("airdeliver.singularity")

# --- 🧱 DOMAIN ENUMS & CONSTANTS ---

class FinancialTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class UserPersona(str, Enum):
    TITANIUM_ELITE = "TITANIUM_ELITE"
    LUXURY_BROWSER = "LUXURY_BROWSER"
    SMART_HUNTER = "SMART_HUNTER"
    VALUE_SEEKER = "VALUE_SEEKER"
    DECISIVE_BUYER = "DECISIVE_BUYER"
    EXPLORER = "EXPLORER"

class SegmentType(str, Enum):
    VIP = "VIP"
    STANDARD = "STANDARD"

# Immutable mapping of Action -> Weight & Index for deterministic tensor embedding
class ActionType(str, Enum):
    VIEW = "view"
    VIEW_IMAGE = "view_image"
    HOVER = "hover"
    SEARCH = "search"
    SEARCH_HIT = "search_hit"
    CART = "cart"
    CHECKOUT = "checkout"
    BUY = "buy"
    DISCARD = "discard"

ACTION_GRAVITY: Dict[ActionType, float] = {
    ActionType.VIEW: 1.0,
    ActionType.VIEW_IMAGE: 1.2,
    ActionType.HOVER: 1.5,
    ActionType.SEARCH: 2.0,
    ActionType.SEARCH_HIT: 2.5,
    ActionType.CART: 5.0,
    ActionType.CHECKOUT: 8.0,
    ActionType.BUY: 10.0,
    ActionType.DISCARD: -5.0
}
# Deterministic index mapping for the Embedding Layer
SORTED_ACTIONS: List[ActionType] = sorted(ACTION_GRAVITY.keys(), key=lambda x: x.value)
ACTION_MAP: Dict[str, int] = {action.value: idx for idx, action in enumerate(SORTED_ACTIONS)}


# --- 📦 DOMAIN TRANSFER OBJECTS (DTOs) ---

class UserProfileMetrics(BaseModel):
    engagement_score: int = 0
    neural_active: bool = False

class UserProfileResult(BaseModel):
    user_id: int
    tier: FinancialTier
    persona: UserPersona
    segment: SegmentType
    metrics: UserProfileMetrics
    meta: Dict[str, str] = Field(default_factory=dict)

class TrackInteractionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, allow_inf_nan=False)
    id: Optional[int] = Field(None, ge=1, le=2147483647)
    price: Optional[float] = Field(None, ge=0)
    vector: Optional[List[float]] = Field(None, alias="vec", min_length=1, max_length=4096)
    image_vector: Optional[List[float]] = Field(None, min_length=1, max_length=4096)

    def get_active_vector(self) -> Optional[List[float]]:
        return self.vector or self.image_vector


# --- 🧠 NEURAL ARCHITECTURE ---

class TemporalEmbedding(nn.Module):
    """Encodes relative time deltas into high-dimensional space."""
    def __init__(self, d_model: int):
        super().__init__()
        self.d_model = d_model
        div_term = torch.exp(torch.arange(0, d_model, 2) * -(math.log(10000.0) / d_model))
        self.register_buffer('div_term_buffer', div_term)

    def forward(self, time_deltas: torch.Tensor) -> torch.Tensor:
        # time_deltas: [batch_size, seq_len]
        scaled_time = torch.log1p(time_deltas.unsqueeze(-1) + 1e-5)
        pe = torch.zeros(time_deltas.size(0), time_deltas.size(1), self.d_model, device=time_deltas.device)
        pe[:, :, 0::2] = torch.sin(scaled_time * self.div_term_buffer)
        pe[:, :, 1::2] = torch.cos(scaled_time * self.div_term_buffer)
        return pe

class OmniNetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    internal_dim: int = Field(1536, ge=4, le=4096)
    intermediate_size: int = Field(6144, ge=4, le=16384)
    heads: int = Field(24, ge=1, le=64)
    layers: int = Field(6, ge=1, le=12)
    dropout: float = Field(0.1, ge=0, lt=1)
    layer_norm_eps: float = Field(1e-6, gt=0, le=0.1)
    supported_dims: Dict[str, int] = {
        "dim_1536": 1536,
        "dim_1152": 1152,
        "dim_1024": 1024,
        "dim_768": 768,
        "dim_512": 512,
        "dim_384": 384
    }

    @model_validator(mode="after")
    def valid_architecture(self):
        if self.internal_dim % 2 or self.internal_dim % self.heads:
            raise ValueError("Model dimension must be even and divisible by the head count")
        if not self.supported_dims or len(self.supported_dims) > 10:
            raise ValueError("Invalid adapter dimensions")
        if any(not 0 < value <= 4096 or key != f"dim_{value}" for key, value in self.supported_dims.items()):
            raise ValueError("Adapter names must identify their positive input dimension")
        return self


class OmniNet(nn.Module):
    """Neural Core mapping multi-modal inputs to a unified Intent Space."""
    def __init__(self, config: OmniNetConfig):
        super().__init__()
        self.config = config

        self.input_adapters = nn.ModuleDict({
            f"dim_{dim}": nn.Identity() if dim == config.internal_dim else nn.Linear(dim, config.internal_dim)
            for dim in config.supported_dims.values()
        })

        self.action_embedding = nn.Embedding(len(ACTION_MAP), config.internal_dim)
        self.time_encoder = TemporalEmbedding(config.internal_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.internal_dim,
            nhead=config.heads,
            dim_feedforward=config.intermediate_size,
            dropout=config.dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True,
            layer_norm_eps=config.layer_norm_eps
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.layers)

        self.intention_projector = nn.Linear(config.internal_dim, config.internal_dim)
        self.negation_projector = nn.Linear(config.internal_dim, config.internal_dim)

    def forward(self, vectors: torch.Tensor, actions: torch.Tensor, times: torch.Tensor, input_dim: int, mask: Optional[torch.Tensor] = None) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor]]:
        adapter_key = f"dim_{input_dim}"
        if adapter_key not in self.input_adapters:
            return None, None

        x = self.input_adapters[adapter_key](vectors)
        x = F.layer_norm(x, (self.config.internal_dim,), eps=self.config.layer_norm_eps)

        act_emb = self.action_embedding(actions)
        time_emb = self.time_encoder(times)

        x = x + act_emb + time_emb
        if mask is None:
            mask = nn.Transformer.generate_square_subsequent_mask(x.size(1), device=x.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        final_state = x[:, -1, :]  # Extract last temporal state

        pos = self.intention_projector(final_state)
        neg = self.negation_projector(final_state)
        return F.normalize(pos, p=2, dim=-1), F.normalize(neg, p=2, dim=-1)


# --- 🚀 CORE SERVICE ---

class BehaviorEngine:
    """
    SOTA Behavioral Orchestrator.
    Manages neural intent resolution, financial DNA parsing, and stream consolidation.
    Replaces implicit globals with explicit lifecycle controls and dependency injection.
    """

    def __init__(
        self, cache: IAsyncCacheClient, net_config: Optional[OmniNetConfig] = None, *,
        checkpoint_path: Optional[str] = None, checkpoint_sha256: Optional[str] = None,
        embedding_sources: Optional[Dict[str, str]] = None,
        allow_untrained_inference: bool = False,
    ):
        self.cache = cache
        settings = get_core_settings()
        self.net_config = net_config or OmniNetConfig()
        self.device = torch.device("cpu")
        self.brain: Optional[OmniNet] = None
        self._model_state: Dict[str, Any] = {
            "state": "untrained", "source": "none", "inference_ready": False,
            "production_approved": False, "model_version": None, "sha256": None,
        }
        self._trained_dims: Set[int] = set()
        self._model_namespace = "unavailable"
        if embedding_sources is None:
            from app.services.ai_commerce_engine import PRODUCT_TEXT_MODEL, PRODUCT_VISION_MODEL
            self.embedding_sources = {
                f"dim_{PRODUCT_TEXT_MODEL.dimension}": f"{PRODUCT_TEXT_MODEL.name}@{settings.PRODUCT_TEXT_MODEL_REVISION or 'unversioned'}",
                f"dim_{PRODUCT_VISION_MODEL.dimension}": f"{PRODUCT_VISION_MODEL.name}@{settings.PRODUCT_VISION_MODEL_REVISION or 'unversioned'}",
            }
        else:
            self.embedding_sources = dict(embedding_sources)
        path = checkpoint_path or settings.BEHAVIOR_CHECKPOINT_PATH
        if path:
            loaded = load_behavior_checkpoint(
                path, expected_sha256=checkpoint_sha256 or settings.BEHAVIOR_CHECKPOINT_SHA256,
                expected_actions=ACTION_MAP, production=settings.APP_ENV == "production",
            )
            manifest = loaded.manifest
            if manifest.training_source == "untrained":
                raise ModelArtifactError("An untrained checkpoint cannot enable behavior inference")
            if net_config is None:
                self.net_config = OmniNetConfig(**manifest.architecture)
            elif net_config.model_dump() != manifest.architecture:
                raise ModelArtifactError("Checkpoint architecture does not match requested model")
            expected_sources = {key: self.embedding_sources.get(key, "unsupported") for key in manifest.embedding_sources}
            if expected_sources != manifest.embedding_sources:
                raise ModelArtifactError("Checkpoint embedding sources do not match configured embedding models")
            if settings.APP_ENV == "production" and any(not re.fullmatch(r"[a-fA-F0-9]{40}", value.rsplit("@", 1)[-1]) for value in expected_sources.values()):
                raise ModelArtifactError("Production behavior requires pinned embedding model revisions")
            if not set(manifest.embedding_sources) <= set(self.net_config.supported_dims):
                raise ModelArtifactError("Checkpoint references an unsupported adapter")
            self.device = self._resolve_device()
            # Meta construction avoids allocating random weights before loading
            # the artifact, and assign avoids a second CPU parameter copy.
            with torch.device("meta"):
                self.brain = OmniNet(self.net_config)
            try:
                self.brain.load_state_dict(loaded.state_dict, strict=True, assign=True)
                self.brain.to(self.device).eval()
            except (RuntimeError, ValueError) as exc:
                raise ModelArtifactError("Checkpoint tensor shapes do not match the architecture") from exc
            self._trained_dims = {int(key[4:]) for key in manifest.embedding_sources}
            self._model_namespace = loaded.sha256[:24]
            self._model_state = {
                "state": "real_validated" if manifest.production_approved else "trained_unvalidated",
                "source": manifest.training_source, "inference_ready": True,
                "production_approved": manifest.production_approved,
                "model_version": manifest.model_version, "sha256": loaded.sha256,
                "evaluation_source": manifest.evaluation_source,
                "evaluation_examples": manifest.evaluation_examples,
                "metrics": dict(manifest.metrics),
            }
        elif allow_untrained_inference:
            if settings.APP_ENV != "development":
                raise ModelArtifactError("Untrained inference is restricted to explicit development tests")
            self.device = self._resolve_device()
            self.brain = OmniNet(self.net_config).to(self.device).eval()
            self._model_namespace = "research-" + uuid.uuid4().hex[:16]
            self._trained_dims = set(self.net_config.supported_dims.values())
            for dim in self._trained_dims:
                self.embedding_sources.setdefault(f"dim_{dim}", "development-research@unversioned")
            self._model_state.update(state="research_only", source="untrained", inference_ready=True)
        else:
            logger.warning("Behavior inference unavailable: no trained checkpoint configured")

        self.synaptic_buffer: asyncio.Queue = asyncio.Queue(maxsize=50000)
        self._shutdown_event = asyncio.Event()
        self._worker_task: Optional[asyncio.Task] = None
        self._background_tasks: set = set()
        self._inference_lock = asyncio.Lock()

    def model_status(self) -> Dict[str, Any]:
        return dict(self._model_state)

    def ghost_key(self, user_id: int) -> str:
        return f"{self._key_ghost(user_id)}:{self._model_namespace}"

    def stream_key(self, user_id: int, dimension: int) -> str:
        source = self.embedding_sources.get(f"dim_{dimension}", "unsupported")
        version = hashlib.sha256(source.encode()).hexdigest()[:16]
        return f"{self._key_stream(user_id, dimension)}:{version}"

    async def get_ghost_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        if self.brain is None or type(user_id) is not int or not 0<user_id<=2147483647:
            return None
        raw = await self.cache.get(self.ghost_key(user_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if not isinstance(data,dict) or data.get("model_id") != self._model_namespace:
                return None
            source=data.get("src_dim")
            if type(source) is not int or source not in self._trained_dims:
                return None
            stamp=data.get("ts")
            if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<stamp<=time.time()+60 or time.time()-stamp>3600:
                return None
            for name in ("pos","neg"):
                vector=data.get(name)
                if not isinstance(vector,list) or len(vector)!=self.net_config.internal_dim:
                    return None
                if not all(type(value) in (int,float) and math.isfinite(value) and abs(value)<=1.00001 for value in vector) or not any(vector):
                    return None
            return data
        except (ValueError, TypeError, AttributeError,OverflowError):
            return None

    def _resolve_device(self) -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return torch.device("mps")
        torch.set_num_threads(min(8, torch.get_num_threads()))
        return torch.device("cpu")

    async def start(self) -> None:
        """Starts the background consolidation loop."""
        if self._worker_task is None or self._worker_task.done():
            self._shutdown_event.clear()
            self._worker_task = asyncio.create_task(self._synaptic_loop())
            logger.info("⚡ BEHAVIOR ENGINE WORKER STARTED.", extra={"device": str(self.device)})

    async def stop(self) -> None:
        """Gracefully halts the background loop."""
        self._shutdown_event.set()
        if self._worker_task:
            await self._worker_task
            logger.info("🛑 BEHAVIOR ENGINE WORKER STOPPED.")
        while self._background_tasks:
            await asyncio.gather(*list(self._background_tasks), return_exceptions=True)

    # --- 🗄️ CACHE NAMESPACE ---
    @staticmethod
    def _key_price_hist(uid: int) -> str: return f"ai:beh:u:{uid}:price_hist"

    @staticmethod
    def _key_seen_24h(uid: int) -> str: return f"ai:beh:u:{uid}:seen_ids_24h"

    @staticmethod
    def _key_ghost(uid: int) -> str: return f"ai:beh:u:{uid}:ghost_v2"

    @staticmethod
    def _key_stream(uid: int, dim: int) -> str: return f"ai:beh:u:{uid}:stream_d{dim}"

    @staticmethod
    def _key_active_dim(uid: int) -> str: return f"ai:beh:u:{uid}:active_dim"

    # --- 🧬 IDENTITY RESOLUTION ---

    async def _analyze_financial_dna(self, user_id: int) -> FinancialTier:
        try:
            prices_raw = await self.cache.client.lrange(self._key_price_hist(user_id), 0, -1)
            if not prices_raw:
                return FinancialTier.MEDIUM

            prices = [float(p) for p in prices_raw]
            avg_price = sum(prices) / len(prices)

            if avg_price > 800.0: return FinancialTier.HIGH
            if avg_price < 150.0: return FinancialTier.LOW
            return FinancialTier.MEDIUM
        except Exception as e:
            logger.warning("Financial DNA fallback triggered.", extra={"user_id": user_id, "error": str(e)})
            return FinancialTier.MEDIUM

    async def analyze_financial_dna(self, user_id: int) -> FinancialTier:
        """Public facade for _analyze_financial_dna.

        The NLU suggestion pipeline calls this exact name (guarded by
        hasattr); without it the guard silently skipped tier analysis and
        every user was treated as MEDIUM.
        """
        return await self._analyze_financial_dna(user_id)

    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves real-time behavioral identity resolving concurrent downstream dependencies.
        Guaranteed to return a deterministic dictionary under any failure condition.
        """
        try:
            dna_future = self._analyze_financial_dna(user_id)
            ghost_future = self.get_ghost_profile(user_id)
            seen_future = self.cache.client.scard(self._key_seen_24h(user_id))

            results = await asyncio.gather(dna_future, ghost_future, seen_future, return_exceptions=True)

            tier: FinancialTier = results[0] if isinstance(results[0], FinancialTier) else FinancialTier.MEDIUM
            ghost_data = results[1] if not isinstance(results[1], Exception) else None
            interaction_vol = results[2] if isinstance(results[2], int) else 0

            has_intent = isinstance(ghost_data, dict) and bool(ghost_data.get("pos"))

            # Intent Classification Matrix
            segment = SegmentType.VIP if tier == FinancialTier.HIGH else SegmentType.STANDARD

            if tier == FinancialTier.HIGH:
                persona = UserPersona.TITANIUM_ELITE if has_intent else UserPersona.LUXURY_BROWSER
            elif tier == FinancialTier.LOW:
                persona = UserPersona.SMART_HUNTER if interaction_vol > 10 else UserPersona.VALUE_SEEKER
            else:
                persona = UserPersona.DECISIVE_BUYER if has_intent else UserPersona.EXPLORER

            profile = UserProfileResult(
                user_id=user_id,
                tier=tier,
                persona=persona,
                segment=segment,
                metrics=UserProfileMetrics(engagement_score=interaction_vol, neural_active=has_intent),
                meta={"engine": "Singularity_v10.0", "latency": "RealTime", "model_state": self._model_state["state"], "model_source": self._model_state["source"]}
            )
            return profile.model_dump()

        except Exception as e:
            logger.error("Critical failure resolving profile. Emitting fallback.", exc_info=True, extra={"user_id": user_id})
            return UserProfileResult(
                user_id=user_id,
                tier=FinancialTier.MEDIUM,
                persona=UserPersona.EXPLORER,
                segment=SegmentType.STANDARD,
                metrics=UserProfileMetrics(),
                meta={"fallback": "True"}
            ).model_dump()

    # --- 📡 EVENT TRACKING ---

    async def register_interaction(self, user_id: int, signal: str, weight: float = 1.0) -> None:
        """Seam adapter: accepts the NLU service's text signals and converts them
        into neural events the OmniNet can learn from.

        The NLU has always called this method (guarded by hasattr), but it never
        existed, so conversational behavioral signals were silently dropped.
        The signal text is embedded with the shared 1536-dim product text model
        (the OmniNet's native internal dimension, Identity adapter) and staged
        through the standard track_interaction path.
        """
        # Validate before native embedding work, not only in track_interaction.
        if type(user_id) is not int or not 0<user_id<=2147483647:
            return
        if not isinstance(signal,str) or not 1<=len(signal.strip())<=4000:
            return
        if isinstance(weight,bool) or not isinstance(weight,(int,float)) or not math.isfinite(weight) or weight<=0:
            return
        signal = signal.strip()
        try:
            from app.services.ai_commerce_engine import ModelRegistry

            model = ModelRegistry().get_text_model()
            vector = await asyncio.to_thread(model.encode, signal, convert_to_numpy=True)
            vec_list = vector.tolist()
        except Exception as exc:
            logger.warning("register_interaction embedding failed", extra={"user_id": user_id, "error_type": type(exc).__name__})
            return

        interaction_type = ActionType.SEARCH_HIT.value if weight >= 2.0 else ActionType.VIEW.value
        await self.track_interaction(user_id, interaction_type, {"vec": vec_list})

    async def track_interaction(self, user_id: int, interaction_type: str, raw_metadata: Dict[str, Any]) -> None:
        """Asynchronously stages an interaction event into the neural buffer."""
        if type(user_id) is not int or user_id<=0 or interaction_type not in ACTION_MAP:
            return
        if not isinstance(raw_metadata,dict):return

        try:
            meta = TrackInteractionPayload(**raw_metadata)
        except ValidationError as e:
            logger.warning("Invalid interaction metadata payload", extra={"error_type": type(e).__name__})
            return

        # Parallel fire-and-forget state updates
        if meta.price is not None:
            task = asyncio.create_task(
                self._update_price_history(user_id, meta.price),
                name=f"update_price_history:{user_id}",
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            task.add_done_callback(self._handle_background_task_result)

        if meta.id is not None:
            task = asyncio.create_task(
                self._update_seen_history(user_id, meta.id),
                name=f"update_seen_history:{user_id}",
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            task.add_done_callback(self._handle_background_task_result)
        
        vector = meta.get_active_vector()
        if not vector:
            return

        dim = len(vector)
        if f"dim_{dim}" not in self.net_config.supported_dims or f"dim_{dim}" not in self.embedding_sources:
            return

        packet = {
            "u": user_id,
            "a": ACTION_MAP[interaction_type],
            "v": vector,
            "d": dim,
            "ts": time.time(),
            "price": meta.price,
            "item_id": meta.id   
        }

        try:
            self.synaptic_buffer.put_nowait(packet)
        except asyncio.QueueFull:
            logger.warning("Synaptic buffer saturation. Dropping event.", extra={"user_id": user_id})

    async def _update_price_history(self, user_id: int, price: float) -> None:
        key = self._key_price_hist(user_id)
        await self.cache.client.lpush(key, str(price))
        await self.cache.client.ltrim(key, 0, 19)

    async def record_product_exposure(self,user_id:int,product_ids) -> None:
        """Observed display only. Never embeds text or infers shopping traits."""
        if type(user_id) is not int or user_id<=0:return
        ids={pid for pid in list(product_ids)[:20] if type(pid) is int and 0<pid<=2147483647}
        if not ids:return
        from app.services.ai_nlu_service import RedisProductFreshnessRepository
        await RedisProductFreshnessRepository(self.cache).mark_products_as_seen(user_id,ids,86400)
        pipe=self.cache.client.pipeline()
        pipe.sadd(self._key_seen_24h(user_id),*[str(pid) for pid in ids])
        pipe.expire(self._key_seen_24h(user_id),86400)
        await pipe.execute()

    async def _update_seen_history(self, user_id: int, item_id: int) -> None:
        key = self._key_seen_24h(user_id)
        await self.cache.sadd(key, str(item_id))
        await self.cache.expire(key, 86400)
    
    def _handle_background_task_result(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            pass  # Task was cancelled, perfectly fine
        except Exception as e:
            logger.error(
                "Background task failed",
                extra={"task_name": task.get_name(), "error": str(e)}
            )
    # --- 🔄 BACKGROUND CONSOLIDATION ---

    async def _synaptic_loop(self) -> None:
        """Drains the interaction queue and commits vectors to distributed storage."""
        while not self._shutdown_event.is_set() or not self.synaptic_buffer.empty():
            batch = []
            while len(batch) < 50:
                try:
                    batch.append(self.synaptic_buffer.get_nowait())
                except asyncio.QueueEmpty:
                    break

            if not batch:
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                continue

            await self._consolidate_memory(batch)

    async def _consolidate_memory(self, batch: List[Dict[str, Any]]) -> None:
        try:
            pipe = self.cache.client.pipeline()
            users_to_update = set()
            stream_ttl_seconds = 86400
            stream_max_len = 64
            price_history_max_len = 20
            header_struct = struct.Struct("di")

            for event in batch:
                if not isinstance(event,dict):
                    continue
                uid = event.get("u")
                dim = event.get("d")
                ts = event.get("ts")
                action = event.get("a")
                vector = event.get("v")

                # Validate again at the drained queue boundary. Never derive a
                # Redis namespace or inference work from coerced packet fields.
                if type(uid) is not int or not 0<uid<=2147483647:
                    continue
                if type(dim) is not int or f"dim_{dim}" not in self.net_config.supported_dims or f"dim_{dim}" not in self.embedding_sources:
                    continue
                if type(action) is not int or not 0<=action<len(ACTION_MAP):
                    continue
                if type(ts) not in (int,float) or not math.isfinite(ts) or not 0<ts<=time.time()+60 or time.time()-ts>86400:
                    continue
                if not isinstance(vector,(list,tuple)) or len(vector)!=dim:
                    continue
                if not all(type(value) in (int,float) and math.isfinite(value) and abs(value)<=3.4028234663852886e38 for value in vector):
                    continue
                price=event.get("price");item_id=event.get("item_id")
                if price is not None and (type(price) not in (int,float) or not math.isfinite(price) or price<0):
                    continue
                if item_id is not None and (type(item_id) is not int or not 0<item_id<=2147483647):
                    continue
                stream_key = self.stream_key(uid, dim)
                active_dim_key = self._key_active_dim(uid)
                try:
                    payload = header_struct.pack(ts, action) + struct.pack(f"{dim}f", *vector)
                except (struct.error,OverflowError):
                    continue
                users_to_update.add(uid)

                # This cache uses decode_responses=True. Persist ASCII rather
                # than arbitrary binary which Redis cannot decode as UTF-8.
                pipe.rpush(stream_key, "b64:" + base64.b64encode(payload).decode("ascii"))
                pipe.ltrim(stream_key, -stream_max_len, -1)
                pipe.expire(stream_key, stream_ttl_seconds)
                pipe.set(active_dim_key, str(dim), ex=stream_ttl_seconds)

                price = event.get("price")
                if price is not None:
                    price_history_key = self._key_price_hist(uid)
                    pipe.lpush(price_history_key, str(price))
                    pipe.ltrim(price_history_key, 0, price_history_max_len - 1)

                item_id = event.get("item_id")
                if item_id is not None:
                    seen_key = self._key_seen_24h(uid)
                    pipe.sadd(seen_key, str(item_id))
                    pipe.expire(seen_key, stream_ttl_seconds)

            # تنفيذ كل العمليات المجمعة في دفعة واحدة للشبكة
            await pipe.execute()

            # تشغيل معالجة أحلام الذكاء الاصطناعي في الخلفية للمستخدمين المحدثين
            for uid in users_to_update:
                task = asyncio.create_task(self._dream_future(uid), name=f"behavior-inference:{uid}")
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
                task.add_done_callback(self._handle_background_task_result)

        except Exception as e:
            logger.error("Memory consolidation pipeline failure", extra={"error": str(e)})

    # --- 🔮 NEURAL INFERENCE ---

    async def _dream_future(self, user_id: int) -> None:
        """Re-evaluates the user's temporal embedding sequence to compute their current 'Ghost'."""
        if self.brain is None:
            return
        try:
            active_dim_str = await self.cache.get(self._key_active_dim(user_id))
            target_dim = int(active_dim_str) if active_dim_str else self.net_config.internal_dim
            if target_dim not in self._trained_dims:
                return
            key = self.stream_key(user_id, target_dim)

            raw_data = await self.cache.client.lrange(key, 0, -1)
            if len(raw_data) < 3:
                return

            vectors, actions, times = [], [], []
            now = time.time()
            expected_len = 12 + (target_dim * 4)

            for blob in raw_data:
                if isinstance(blob, str):
                    if not blob.startswith("b64:"):
                        continue
                    try:
                        blob = base64.b64decode(blob[4:], validate=True)
                    except (ValueError, TypeError):
                        continue
                if len(blob) != expected_len:
                    continue  # Protect against memory corruption or dimension shifts

                ts, act = struct.unpack("di", blob[:12])
                vec = struct.unpack(f"{target_dim}f", blob[12:])
                if not 0 <= act < len(ACTION_MAP) or not all(math.isfinite(value) for value in vec):
                    continue
                vectors.append(vec)
                actions.append(act)
                times.append(max(0.0, now - ts))

            if not vectors:
                return

            def infer():
                v_t = torch.tensor([vectors], dtype=torch.float32, device=self.device)
                a_t = torch.tensor([actions], dtype=torch.long, device=self.device)
                t_t = torch.tensor([times], dtype=torch.float32, device=self.device)
                with torch.no_grad():
                    return self.brain(v_t, a_t, t_t, input_dim=target_dim)

            # Keep CPU/GPU inference off the async message-processing loop and
            # bound simultaneous access to this shared model instance.
            async with self._inference_lock:
                pos_ghost, neg_ghost = await asyncio.to_thread(infer)

            if pos_ghost is None or neg_ghost is None:
                return

            ghost_data = {
                "pos": pos_ghost.cpu().numpy().tolist()[0],
                "neg": neg_ghost.cpu().numpy().tolist()[0],
                "src_dim": target_dim,
                "model_id": self._model_namespace,
                "ts": now
            }
            await self.cache.set(self.ghost_key(user_id), json.dumps(ghost_data), ttl=3600)

        except Exception as e:
            logger.error("Ghost sequence generation failed", extra={"user_id": user_id, "error": str(e)})

    async def collapse_wavefunction(self, user_id: int, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-ranks inventory candidates based on semantic distance to the user's current Ghost vector.
        Operates strictly in batch mode to maximize GPU/MPS throughput.
        """
        if self.brain is None:
            return candidates
        ghost = await self.get_ghost_profile(user_id)
        if not ghost:
            return candidates

        try:
            pos_vec = torch.tensor(ghost['pos'], device=self.device)
            neg_vec = torch.tensor(ghost['neg'], device=self.device)

            valid_cands, cand_vectors = [], []

            for i, p in enumerate(candidates):
                v = p.get('vector') or p.get('image_vector') or p.get('embedding')
                if not v:
                    continue

                v_dim = len(v)
                if v_dim not in self._trained_dims:
                    continue
                adapter_key = f"dim_{v_dim}"

                if v_dim == self.net_config.internal_dim:
                    cand_vectors.append(v)
                    valid_cands.append(i)
                elif adapter_key in self.brain.input_adapters:
                    with torch.no_grad():
                        v_t = torch.tensor(v, dtype=torch.float32, device=self.device)
                        v_adapted = self.brain.input_adapters[adapter_key](v_t)
                        v_adapted = F.layer_norm(v_adapted, (self.net_config.internal_dim,), eps=self.net_config.layer_norm_eps)
                        cand_vectors.append(v_adapted.cpu().tolist())
                        valid_cands.append(i)

            if not cand_vectors:
                return candidates

            c_t = torch.tensor(cand_vectors, device=self.device)
            desire = F.cosine_similarity(pos_vec.unsqueeze(0), c_t)
            aversion = F.cosine_similarity(neg_vec.unsqueeze(0), c_t)
            scores = (desire - (aversion * 0.4)).tolist()

            for list_idx, original_idx in enumerate(valid_cands):
                score = scores[list_idx]
                candidates[original_idx]['_ai_score'] = score
                if score > 0.6:
                    candidates[original_idx]['_ai_badge'] = "Best Match"
                elif score > 0.4:
                    candidates[original_idx]['_ai_badge'] = "Recommended"

            # In-place sorting to maintain references for the orchestrating caller
            candidates.sort(key=lambda x: x.get('_ai_score', -1.0), reverse=True)
            return candidates

        except Exception as e:
            logger.error("Wavefunction collapse failed", extra={"user_id": user_id, "error": str(e)})
            return candidates
