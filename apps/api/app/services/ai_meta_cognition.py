# apps/api/app/services/ai_meta_cognition.py

import numpy as np
import logging
from typing import Dict, List, Any, Optional

# إعداد الـ Logger ليكون منفصلاً عن باقي النظام لتسهيل المراقبة
logger = logging.getLogger("airdeliver.meta_cognition")

class MetaCognitionLayer:
    """
    🧘 THE CONSCIENCE OF THE SYSTEM (Layer 0 - Epistemic Engine).
    
    Architectural Purpose:
    Acts as a 'Circuit Breaker' for AI Hallucinations and Overconfidence.
    It evaluates 'Epistemic Uncertainty' (Unknown Unknowns) by measuring the 
    drift between the user's historical 'Ghost' and their current session vector.

    Outputs:
    - AUTHORITATIVE: System is confident (Prediction Mode).
    - INQUISITIVE: System is confused (Exploration Mode).
    - ADAPTIVE_SHOCK: Context shift detected (Validation Mode).
    """
    
    _instance = None

    def __new__(cls):
        """Singleton Pattern to ensure only one Conscience exists in memory."""
        if cls._instance is None:
            cls._instance = super(MetaCognitionLayer, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # --- ⚙️ HYPER-PARAMETERS (معايير الشك) ---
        # 1. Uncertainty Threshold (0.65):
        # إذا زاد الشك عن 65%، يتوقف النظام عن البيع ويبدأ في طرح الأسئلة.
        self.uncertainty_threshold = 0.65  
        
        # 2. Drift Tolerance (0.8):
        # المسافة المسموحة بين "ماضي المستخدم" و"سلوكه الحالي" قبل اعتبارها حالة طارئة.
        self.drift_tolerance = 0.8         

    def evaluate_confidence(self, user_ghost: Dict[str, Any], current_session_vector: List[float]) -> Dict[str, Any]:
        """
        🚀 EPISTEMIC AUDIT: The Core Logic.
        Performs vector math to determine the 'State of Mind' of the AI agent.
        
        Args:
            user_ghost: The predictive profile from Behavior Engine (Pos/Neg vectors).
            current_session_vector: The embedding of the user's current query/action.
            
        Returns:
            Dict containing 'stance', 'uncertainty', and 'action_directive'.
        """
        
        # 🛡️ 1. COLD START GUARD (حماية البداية الباردة)
        # إذا لم يكن لدينا بيانات كافية، نتبنى وضع الفضول فوراً.
        if not user_ghost or not current_session_vector:
            return {
                "uncertainty": 1.0, 
                "drift": 0.0,
                "stance": "INQUISITIVE", 
                "action_directive": "BROADEN_SEARCH_HORIZON",
                "reason": "Cold Start / No Data"
            }

        try:
            # 🛡️ 2. DATA SANITIZATION & DIMENSIONALITY CHECK
            # استخراج المتجهات وتحويلها لمصفوفات NumPy للحساب السريع
            ghost_pos_list = user_ghost.get('pos', [])
            
            # التأكد من أن القوائم ليست فارغة
            if not ghost_pos_list or not current_session_vector:
                return {"uncertainty": 0.5, "stance": "AUTHORITATIVE", "reason": "Empty Vectors"}

            ghost_pos = np.array(ghost_pos_list, dtype=np.float32)
            current_vec = np.array(current_session_vector, dtype=np.float32)
            
            # حماية حرجة: هل الأبعاد متطابقة؟ (مثلاً 1536 vs 1536)
            # إذا اختلفت الأبعاد، لا يمكن حساب المسافة.
            if ghost_pos.shape != current_vec.shape:
                logger.warning(f"⚠️ Dimensionality Mismatch in Meta-Cognition: Ghost {ghost_pos.shape} vs Current {current_vec.shape}")
                # نعود للوضع الآمن بدلاً من الانهيار
                return {"uncertainty": 0.5, "stance": "AUTHORITATIVE", "reason": "Dimension Mismatch Fallback"}

            # 🧮 3. THE MATH (Euclidean Drift Calculation)
            # حساب المسافة الإقليدية: كلما زاد الرقم، زاد اختلاف "الحاضر" عن "الماضي"
            drift_distance = float(np.linalg.norm(ghost_pos - current_vec))
            
            # 📊 4. HISTORICAL CONFIDENCE WEIGHTING
            # هل الشبح نفسه مبني على بيانات قوية؟ (default to 0.8 if missing)
            historical_confidence = float(user_ghost.get('confidence', 0.8))

            # 🧠 5. THE EPISTEMIC EQUATION (معادلة الشك المعرفي)
            # الشك = (الانحراف الحالي * 70%) + (ضعف الثقة التاريخية * 30%)
            # هذه المعادلة توازن بين "ما تفعله الآن" وبين "مدى معرفتي بك سابقاً"
            uncertainty_score = (drift_distance * 0.7) + ((1.0 - historical_confidence) * 0.3)

            # 🚦 6. THE DECISION MATRIX (تحديد الموقف الاستراتيجي)
            stance = "AUTHORITATIVE"        # Default: Confident & Selling
            action_directive = "COLLAPSE_WAVEFUNCTION"
            reason = "Stable Behavior"

            if uncertainty_score > self.uncertainty_threshold:
                # الحالة أ: النظام لا يفهم ماذا يحدث (شك عالي)
                # التصرف: التوقف عن الفلترة، توسيع البحث، وطرح أسئلة استكشافية.
                stance = "INQUISITIVE"
                action_directive = "BROADEN_SEARCH_HORIZON"
                reason = f"High Uncertainty ({uncertainty_score:.2f})"
            
            elif drift_distance > self.drift_tolerance:
                # الحالة ب: المستخدم يتصرف عكس عادته (انحراف عالي رغم الثقة السابقة)
                # التصرف: صدمة تكيفية، الاعتراف بالتغيير، ومحاولة بناء جسر للسياق الجديد.
                stance = "ADAPTIVE_SHOCK"
                action_directive = "TRIGGER_CLARIFICATION"
                reason = f"Context Drift Detected ({drift_distance:.2f})"

            # ✅ 7. FINAL PAYLOAD CONSTRUCTION
            # نستخدم float() لضمان أن الأرقام ليست numpy types (لتفادي مشاكل JSON)
            result = {
                "uncertainty": float(uncertainty_score),
                "drift": float(drift_distance),
                "stance": stance,
                "action_directive": action_directive,
                "reason": reason,
                "meta": {
                    "engine": "MetaCognition_v1.0",
                    "historical_conf": historical_confidence
                }
            }
            
            # Log only on significant shifts to reduce noise
            if stance != "AUTHORITATIVE":
                logger.info(f"🧘 Meta-Cognition Shift: {result}")
                
            return result

        except Exception as e:
            # 🛡️ FAIL-OPEN PROTOCOL
            # في أسوأ الظروف (خطأ في numpy، ذاكرة، الخ)، نفترض أننا واثقون لنكمل البيع
            logger.error(f"🔥 Meta-Cognition Critical Failure: {e}", exc_info=True)
            return {
                "uncertainty": 0.0, 
                "stance": "AUTHORITATIVE", 
                "action_directive": "SAFE_MODE",
                "reason": "System Error Protection"
            }
