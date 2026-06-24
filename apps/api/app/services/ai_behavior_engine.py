# apps/api/app/services/ai_behavior_engine.py

import asyncio
import json
import logging
import math
import struct
import time
from enum import Enum
from typing import List, Dict, Optional, Any, Set, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, Field, ValidationError

from app.services.cache_service import IAsyncCacheClient

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
    id: Optional[int] = None
    price: Optional[float] = None
    vector: Optional[List[float]] = Field(None, alias="vec")
    image_vector: Optional[List[float]] = None

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
    internal_dim: int = 1536
    intermediate_size: int = 6144
    heads: int = 24
    layers: int = 6
    dropout: float = 0.1
    layer_norm_eps: float = 1e-6
    supported_dims: Dict[str, int] = {
        "dim_1536": 1536,
        "dim_1152": 1152,
        "dim_1024": 1024,
        "dim_768": 768,
        "dim_512": 512,
        "dim_384": 384
    }

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

    def __init__(self, cache: IAsyncCacheClient):
        self.cache = cache
        self.device = self._resolve_device()

        self.net_config = OmniNetConfig()
        self.brain = OmniNet(self.net_config).to(self.device)
        self.brain.eval()

        self.synaptic_buffer: asyncio.Queue = asyncio.Queue(maxsize=50000)
        self._shutdown_event = asyncio.Event()
        self._worker_task: Optional[asyncio.Task] = None

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

    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves real-time behavioral identity resolving concurrent downstream dependencies.
        Guaranteed to return a deterministic dictionary under any failure condition.
        """
        try:
            dna_future = self._analyze_financial_dna(user_id)
            ghost_future = self.cache.get(self._key_ghost(user_id))
            seen_future = self.cache.client.scard(self._key_seen_24h(user_id))

            results = await asyncio.gather(dna_future, ghost_future, seen_future, return_exceptions=True)

            tier: FinancialTier = results[0] if isinstance(results[0], FinancialTier) else FinancialTier.MEDIUM
            ghost_data = results[1] if not isinstance(results[1], Exception) else None
            interaction_vol = results[2] if isinstance(results[2], int) else 0

            has_intent = isinstance(ghost_data, str) and len(ghost_data) > 10

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
                meta={"engine": "Singularity_v10.0", "latency": "RealTime"}
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

    async def track_interaction(self, user_id: int, interaction_type: str, raw_metadata: Dict[str, Any]) -> None:
        """Asynchronously stages an interaction event into the neural buffer."""
        if interaction_type not in ACTION_MAP:
            return

        try:
            meta = TrackInteractionPayload(**raw_metadata)
        except ValidationError as e:
            logger.warning("Invalid interaction metadata payload", extra={"error": str(e), "user_id": user_id})
            return

        # Parallel fire-and-forget state updates
        update_tasks = []
        if meta.price is not None:
            update_tasks.append(self._update_price_history(user_id, meta.price))
        if meta.id is not None:
            update_tasks.append(self._update_seen_history(user_id, meta.id))

        if update_tasks:
            asyncio.create_task(asyncio.gather(*update_tasks, return_exceptions=True))

        vector = meta.get_active_vector()
        if not vector:
            return

        dim = len(vector)
        if f"dim_{dim}" not in self.net_config.supported_dims:
            return

        packet = {
            "u": user_id,
            "a": ACTION_MAP[interaction_type],
            "v": vector,
            "d": dim,
            "ts": time.time()
        }

        try:
            self.synaptic_buffer.put_nowait(packet)
        except asyncio.QueueFull:
            logger.warning("Synaptic buffer saturation. Dropping event.", extra={"user_id": user_id})

    async def _update_price_history(self, user_id: int, price: float) -> None:
        key = self._key_price_hist(user_id)
        await self.cache.client.lpush(key, str(price))
        await self.cache.client.ltrim(key, 0, 19)

    async def _update_seen_history(self, user_id: int, item_id: int) -> None:
        key = self._key_seen_24h(user_id)
        await self.cache.sadd(key, str(item_id))
        await self.cache.expire(key, 86400)

    # --- 🔄 BACKGROUND CONSOLIDATION ---

    async def _synaptic_loop(self) -> None:
        """Drains the interaction queue and commits vectors to distributed storage."""
        while not self._shutdown_event.is_set():
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
            users_to_update: Set[int] = set()

            for event in batch:
                uid, dim = event['u'], event['d']
                users_to_update.add(uid)
                key = self._key_stream(uid, dim)

                # Binary packing: double (8) + int (4) + (dim * floats)
                header = struct.pack("di", event['ts'], event['a'])
                vec_bytes = struct.pack(f"{dim}f", *event['v'])
                blob = header + vec_bytes

                pipe.rpush(key, blob)
                pipe.ltrim(key, -64, -1)  # Bounded history window
                pipe.expire(key, 86400)
                pipe.set(self._key_active_dim(uid), str(dim), ex=86400)

            await pipe.execute()

            # Trigger asynchronous dream state generation for updated users
            for uid in users_to_update:
                asyncio.create_task(self._dream_future(uid))
        except Exception as e:
            logger.error("Memory consolidation pipeline failure", extra={"error": str(e)})

    # --- 🔮 NEURAL INFERENCE ---

    async def _dream_future(self, user_id: int) -> None:
        """Re-evaluates the user's temporal embedding sequence to compute their current 'Ghost'."""
        try:
            active_dim_str = await self.cache.get(self._key_active_dim(user_id))
            target_dim = int(active_dim_str) if active_dim_str else self.net_config.internal_dim
            key = self._key_stream(user_id, target_dim)

            raw_data = await self.cache.client.lrange(key, 0, -1)
            if len(raw_data) < 3:
                return

            vectors, actions, times = [], [], []
            now = time.time()
            expected_len = 12 + (target_dim * 4)

            for blob in raw_data:
                if len(blob) != expected_len:
                    continue  # Protect against memory corruption or dimension shifts

                ts, act = struct.unpack("di", blob[:12])
                vec = struct.unpack(f"{target_dim}f", blob[12:])
                vectors.append(vec)
                actions.append(act)
                times.append(max(0.0, now - ts))

            if not vectors:
                return

            v_t = torch.tensor([vectors], dtype=torch.float32, device=self.device)
            a_t = torch.tensor([actions], dtype=torch.long, device=self.device)
            t_t = torch.tensor([times], dtype=torch.float32, device=self.device)

            with torch.no_grad():
                pos_ghost, neg_ghost = self.brain(v_t, a_t, t_t, input_dim=target_dim)

            if pos_ghost is None or neg_ghost is None:
                return

            ghost_data = {
                "pos": pos_ghost.cpu().numpy().tolist()[0],
                "neg": neg_ghost.cpu().numpy().tolist()[0],
                "src_dim": target_dim,
                "ts": now
            }
            await self.cache.set(self._key_ghost(user_id), json.dumps(ghost_data), ttl=3600)

        except Exception as e:
            logger.error("Ghost sequence generation failed", extra={"user_id": user_id, "error": str(e)})

    async def collapse_wavefunction(self, user_id: int, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-ranks inventory candidates based on semantic distance to the user's current Ghost vector.
        Operates strictly in batch mode to maximize GPU/MPS throughput.
        """
        ghost_json = await self.cache.get(self._key_ghost(user_id))
        if not ghost_json:
            return candidates

        try:
            ghost = json.loads(ghost_json)
            pos_vec = torch.tensor(ghost['pos'], device=self.device)
            neg_vec = torch.tensor(ghost['neg'], device=self.device)

            valid_cands, cand_vectors = [], []

            for i, p in enumerate(candidates):
                v = p.get('vector') or p.get('image_vector') or p.get('embedding')
                if not v:
                    continue

                v_dim = len(v)
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
