# apps/api/app/services/ai_behavior_engine.py

import logging
import asyncio
import time
import random
import struct
import math
import json
from typing import List, Dict, Optional, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from app.services.cache_service import IAsyncCacheClient

# --- 💎 SOTA TITANIUM CONSTANTS ---
# Core Dimensions aligned with Qwen2 (1536) and SigLIP (1152)
INTERNAL_DIM = 1536          
INTERMEDIATE_SIZE = 6144     
HEADS = 24                   
LAYERS = 6                   
DROPOUT = 0.1
LAYER_NORM_EPS = 1e-6        

# PHYSICS ENGINE: Action Weights
ACTION_GRAVITY = {
    "view": 1.0,
    "view_image": 1.2,
    "hover": 1.5,
    "search": 2.0,
    "search_hit": 2.5,
    "cart": 5.0,
    "checkout": 8.0,
    "buy": 10.0,
    "discard": -5.0
}
SORTED_ACTIONS = sorted(ACTION_GRAVITY.keys())
ACTION_MAP = {k: i for i, k in enumerate(SORTED_ACTIONS)}

logger = logging.getLogger("airdeliver.singularity")
logger.setLevel(logging.WARNING)

class TemporalEmbedding(nn.Module):
    def __init__(self, d_model):
        super().__init__()
        self.div_term = torch.exp(torch.arange(0, d_model, 2) * -(math.log(10000.0) / d_model))
        self.register_buffer('div_term_buffer', self.div_term)

    def forward(self, time_deltas):
        scaled_time = torch.log1p(time_deltas.unsqueeze(-1) + 1e-5)
        pe = torch.zeros(time_deltas.size(0), time_deltas.size(1), INTERNAL_DIM).to(time_deltas.device)
        pe[:, :, 0::2] = torch.sin(scaled_time * self.div_term_buffer)
        pe[:, :, 1::2] = torch.cos(scaled_time * self.div_term_buffer)
        return pe

class OmniNet(nn.Module):
    """
    Neural Core that adapts various vector dimensions (Text/Image) into a unified Intent Space.
    """
    def __init__(self):
        super().__init__()
        # Dynamic Adapters for Multi-Modal Inputs
        self.input_adapters = nn.ModuleDict({
            "dim_1536": nn.Identity(),                 # Qwen2 Native
            "dim_1152": nn.Linear(1152, INTERNAL_DIM), # SigLIP Vision
            "dim_1024": nn.Linear(1024, INTERNAL_DIM), # BGE-M3
            "dim_768":  nn.Linear(768, INTERNAL_DIM),  # Legacy
            "dim_512":  nn.Linear(512, INTERNAL_DIM),  # CLIP-B
            "dim_384":  nn.Linear(384, INTERNAL_DIM)   # Small Embedding
        })
        
        self.action_embedding = nn.Embedding(len(ACTION_GRAVITY), INTERNAL_DIM)
        self.time_encoder = TemporalEmbedding(INTERNAL_DIM)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=INTERNAL_DIM, nhead=HEADS, dim_feedforward=INTERMEDIATE_SIZE,
            dropout=DROPOUT, activation='gelu', batch_first=True, norm_first=True, layer_norm_eps=LAYER_NORM_EPS
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=LAYERS)
        
        # Intent Projections
        self.intention_projector = nn.Linear(INTERNAL_DIM, INTERNAL_DIM)
        self.negation_projector = nn.Linear(INTERNAL_DIM, INTERNAL_DIM)

    def forward(self, vectors, actions, times, input_dim=1536, mask=None):
        adapter_key = f"dim_{input_dim}"
        if adapter_key in self.input_adapters:
            x = self.input_adapters[adapter_key](vectors)
        else:
            if vectors.shape[-1] == INTERNAL_DIM: x = vectors
            else: return None, None

        x = F.layer_norm(x, (INTERNAL_DIM,), eps=LAYER_NORM_EPS)
        act_emb = self.action_embedding(actions)
        time_emb = self.time_encoder(times)
        x = x + act_emb + time_emb
        x = self.transformer(x, mask=mask, is_causal=True)
        final_state = x[:, -1, :]
        
        pos = self.intention_projector(final_state)
        neg = self.negation_projector(final_state)
        return F.normalize(pos, p=2, dim=-1), F.normalize(neg, p=2, dim=-1)

class BehaviorEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance: cls._instance = super(BehaviorEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self, cache: IAsyncCacheClient):
        if hasattr(self, 'cache'): return
        self.cache = cache
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.device.type == 'cpu': torch.set_num_threads(4)
        
        self.brain = OmniNet().to(self.device)
        self.brain.eval()
        
        self.synaptic_buffer = asyncio.Queue(maxsize=50000)
        asyncio.create_task(self._synaptic_loop())
        logging.info(f"血 BEHAVIOR ENGINE ONLINE. Device: {self.device}")

    # --- 💎 FINANCIAL DNA ANALYZER ---
    async def analyze_financial_dna(self, user_id: int) -> str:
        """Determines if user is HIGH, MEDIUM, or LOW spender based on view history."""
        key = f"u:{user_id}:price_history"
        try:
            prices = await self.cache.client.lrange(key, 0, -1)
            if not prices: return "MEDIUM"
            
            prices_float = [float(p) for p in prices]
            avg_price = sum(prices_float) / len(prices_float)
            
            if avg_price > 800: return "HIGH"
            if avg_price < 150: return "LOW"
            return "MEDIUM"
        except Exception:
            return "MEDIUM"

    async def get_user_profile(self, user_id: int) -> Dict:
        """
        🚀 HYPER-SCALAR IDENTITY RESOLUTION.
        Performs parallel retrieval of Financial DNA, Neural Ghost Context, and
        Real-time Intent to construct a 'Live Persona' in < 5ms.
        """
        try:
            # 1. ⚡ Parallel Fan-Out (تقنية جوجل لتقليل زمن الاستجابة)
            # نطلق كل الاستعلامات في نفس اللحظة ولا ننتظرها بالتتابع
            dna_future = self.analyze_financial_dna(user_id)
            ghost_future = self.cache.get(f"u:{user_id}:ghost_v2")
            seen_future = self.cache.client.scard(f"u:{user_id}:seen_ids_24h") # حجم التفاعل

            # نجمع النتائج دفعة واحدة (Non-blocking Gather)
            financial_tier, ghost_json, interaction_volume = await asyncio.gather(
                dna_future, ghost_future, seen_future, return_exceptions=True
            )

            # 2. 🧬 Data Sanitization & Fallbacks
            # لو حصل خطأ في استرجاع الـ DNA، نعتبره MEDIUM
            if isinstance(financial_tier, Exception): financial_tier = "MEDIUM"
            if isinstance(interaction_volume, Exception): interaction_volume = 0

            # تحليل الشبح الرقمي (Neural Intent)
            has_strong_intent = False
            if isinstance(ghost_json, str):
                has_strong_intent = True # العميل لديه ملف تنبؤي نشط

            # 3. 💎 The Matrix Classification Algorithm (الخوارزمية التصنيفية)
            # دمج القدرة الشرائية مع السلوك اللحظي
            persona_code = "EXPLORER"
            segment_type = "STANDARD"

            if financial_tier == "HIGH":
                segment_type = "VIP"
                if has_strong_intent:
                    persona_code = "TITANIUM_ELITE"  # غني + يعرف ماذا يريد
                else:
                    persona_code = "LUXURY_BROWSER"  # غني + يتصفح فقط

            elif financial_tier == "LOW":
                if interaction_volume > 10:
                    persona_code = "SMART_HUNTER"    # يبحث عن صفقات بذكاء
                else:
                    persona_code = "VALUE_SEEKER"

            else: # MEDIUM
                if has_strong_intent:
                    persona_code = "DECISIVE_BUYER"
                else:
                    persona_code = "EXPLORER"

            # 4. 📦 Optimized Payload Construction
            return {
                "user_id": user_id,
                "tier": financial_tier,       # HIGH, MEDIUM, LOW
                "persona": persona_code,      # التصنيف النفسي الدقيق
                "segment": segment_type,      # VIP vs STANDARD
                "metrics": {
                    "engagement_score": interaction_volume if isinstance(interaction_volume, int) else 0,
                    "neural_active": has_strong_intent
                },
                "meta": {
                    "engine": "Singularity_v9.1",
                    "latency": "RealTime"
                }
            }

        except Exception as e:
            # 🛡️ Fail-Open Strategy (استراتيجية عدم الانهيار)
            # حتى لو احترق السيرفر، العميل لن يشعر بشيء
            logging.error(f"⚠️ Profile Resolution Fallback: {e}")
            return {
                "tier": "MEDIUM",
                "persona": "EXPLORER",
                "segment": "STANDARD",
                "meta": {"fallback": True}
            }

    async def get_recently_seen_ids(self, user_id: int) -> List[int]:
        key = f"u:{user_id}:seen_ids_24h"
        try:
            ids = await self.cache.smembers(key)
            return [int(i) for i in ids] if ids else []
        except: return []

    # --- CORE TRACKING ---
    async def track_interaction(self, user_id: int, interaction_type: str, metadata: Dict):
        if interaction_type not in ACTION_MAP: return
        
        # 1. Store Price for DNA Analysis
        if metadata.get('price'):
            try:
                await self.cache.client.lpush(f"u:{user_id}:price_history", str(metadata['price']))
                await self.cache.client.ltrim(f"u:{user_id}:price_history", 0, 19) # Keep last 20
            except: pass

        # 2. Store ID for Freshness Logic
        if metadata.get('id'):
            try:
                await self.cache.sadd(f"u:{user_id}:seen_ids_24h", str(metadata['id']))
                await self.cache.expire(f"u:{user_id}:seen_ids_24h", 86400)
            except: pass

        # 3. Vector Processing
        vector = metadata.get('vec') or metadata.get('vector') or metadata.get('image_vector')
        if not vector: return 

        dim = len(vector)
        if f"dim_{dim}" not in self.brain.input_adapters and dim != INTERNAL_DIM: return

        packet = {
            "u": user_id,
            "a": ACTION_MAP[interaction_type],
            "v": vector,
            "d": dim,
            "ts": time.time()
        }
        try: self.synaptic_buffer.put_nowait(packet)
        except asyncio.QueueFull: pass

    # NLU Compatibility (Stub)
    async def register_interaction(self, user_id: int, description: str, weight: float = 1.0):
        pass 

    # --- STORAGE & CONSOLIDATION ---
    async def _synaptic_loop(self):
        while True:
            batch = []
            try:
                for _ in range(50): batch.append(self.synaptic_buffer.get_nowait())
            except asyncio.QueueEmpty:
                if not batch:
                    await asyncio.sleep(0.1)
                    continue
            if batch: await self._consolidate_memory(batch)

    async def _consolidate_memory(self, batch: List[Dict]):
        try:
            pipe = self.cache.client.pipeline()
            users_to_update = set()
            for event in batch:
                uid, dim = event['u'], event['d']
                users_to_update.add(uid)
                key = f"u:{uid}:stream_d{dim}"
                
                header = struct.pack("di", event['ts'], event['a'])
                vec_bytes = struct.pack(f"{dim}f", *event['v'])
                blob = header + vec_bytes
                
                pipe.rpush(key, blob)
                pipe.ltrim(key, -64, -1)
                pipe.expire(key, 86400)
                pipe.set(f"u:{uid}:active_dim", str(dim), ex=86400)
            
            await pipe.execute()
            for uid in users_to_update: asyncio.create_task(self._dream_future(uid))
        except: pass

    # --- PREDICTION (THE GHOST) ---
    async def _dream_future(self, user_id: int):
        try:
            active_dim_str = await self.cache.get(f"u:{user_id}:active_dim")
            target_dim = int(active_dim_str) if active_dim_str else INTERNAL_DIM
            key = f"u:{user_id}:stream_d{target_dim}"
            
            raw_data = await self.cache.client.lrange(key, 0, -1)
            if len(raw_data) < 3: return

            vectors, actions, times = [], [], []
            now = time.time()
            for blob in raw_data:
                ts, act = struct.unpack("di", blob[:12])
                vec = struct.unpack(f"{target_dim}f", blob[12:])
                vectors.append(vec)
                actions.append(act)
                times.append(max(0, now - ts))
            
            v_t = torch.tensor([vectors], dtype=torch.float32).to(self.device)
            a_t = torch.tensor([actions], dtype=torch.long).to(self.device)
            t_t = torch.tensor([times], dtype=torch.float32).to(self.device)

            with torch.no_grad():
                pos_ghost, neg_ghost = self.brain(v_t, a_t, t_t, input_dim=target_dim)
            if pos_ghost is None: return

            ghost_data = {
                "pos": pos_ghost.cpu().numpy().tolist()[0],
                "neg": neg_ghost.cpu().numpy().tolist()[0],
                "src_dim": target_dim,
                "ts": now
            }
            await self.cache.set(f"u:{user_id}:ghost_v2", json.dumps(ghost_data), ttl=3600)
        except: pass

    async def collapse_wavefunction(self, user_id: int, candidates: List[Dict]) -> List[Dict]:
        """ Re-ranks a list of products based on the user's Ghost profile """
        ghost_json = await self.cache.get(f"u:{user_id}:ghost_v2")
        if not ghost_json: return candidates

        try:
            ghost = json.loads(ghost_json)
            pos_vec = torch.tensor(ghost['pos']).to(self.device)
            neg_vec = torch.tensor(ghost['neg']).to(self.device)
            
            valid_cands, cand_vectors = [], []
            for i, p in enumerate(candidates):
                v = p.get('vector') or p.get('image_vector') or p.get('embedding')
                if not v: continue
                
                v_dim = len(v)
                if v_dim == INTERNAL_DIM:
                    cand_vectors.append(v)
                    valid_cands.append(i)
                elif f"dim_{v_dim}" in self.brain.input_adapters:
                    with torch.no_grad():
                        v_t = torch.tensor(v, dtype=torch.float32).to(self.device)
                        v_adapted = self.brain.input_adapters[f"dim_{v_dim}"](v_t)
                        v_adapted = F.layer_norm(v_adapted, (INTERNAL_DIM,), eps=LAYER_NORM_EPS)
                        cand_vectors.append(v_adapted.cpu().tolist())
                        valid_cands.append(i)

            if not cand_vectors: return candidates
            
            c_t = torch.tensor(cand_vectors).to(self.device)
            desire = F.cosine_similarity(pos_vec.unsqueeze(0), c_t)
            aversion = F.cosine_similarity(neg_vec.unsqueeze(0), c_t)
            scores = (desire - (aversion * 0.4)).tolist()

            for list_idx, original_idx in enumerate(valid_cands):
                score = scores[list_idx]
                candidates[original_idx]['_ai_score'] = score
                if score > 0.6: candidates[original_idx]['_ai_badge'] = "識 Best Match"
                elif score > 0.4: candidates[original_idx]['_ai_badge'] = "総 Recommended"

            candidates.sort(key=lambda x: x.get('_ai_score', -1), reverse=True)
            return candidates
        except Exception: return candidates

    async def get_next_best_action(self, user_id: int) -> Optional[Dict]:
        return None 

def get_behavior_engine(cache):
    return BehaviorEngine(cache)
