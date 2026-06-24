# apps/api/app/services/ai_meta_cognition.py

import logging
from enum import Enum
from typing import List, Dict, Any, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

# Configured for structured logging ingestion (e.g., Datadog, ELK)
logger = logging.getLogger("airdeliver.meta_cognition")


# --- DOMAIN ENUMS ---

class CognitiveStance(str, Enum):
    """Represents the epistemic state of the AI system."""
    AUTHORITATIVE = "AUTHORITATIVE"   # Confident, standard prediction mode
    INQUISITIVE = "INQUISITIVE"       # Confused, requires exploration
    ADAPTIVE_SHOCK = "ADAPTIVE_SHOCK" # Sudden context shift detected
    SAFE_MODE = "SAFE_MODE"           # Hardware/Math fault, fail-open state


class ActionDirective(str, Enum):
    """Operational directives outputted to the orchestration layer."""
    COLLAPSE_WAVEFUNCTION = "COLLAPSE_WAVEFUNCTION"   # Proceed with transaction
    BROADEN_SEARCH_HORIZON = "BROADEN_SEARCH_HORIZON" # Ask qualifying questions
    TRIGGER_CLARIFICATION = "TRIGGER_CLARIFICATION"   # Acknowledge shift and verify
    FAIL_OPEN = "FAIL_OPEN"                           # Bypass meta-cognition safely


# --- DOMAIN MODELS (BOUNDARY VALIDATION) ---

class MetaCognitionConfig(BaseModel):
    """Hyperparameters for the Epistemic Engine, easily injectable and environment-driven."""
    uncertainty_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    drift_tolerance: float = Field(default=0.8, ge=0.0)
    drift_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_weights(self) -> "MetaCognitionConfig":
        """Ensure the epistemic equation weights sum to exactly 1.0 for normalized scoring."""
        total = self.drift_weight + self.confidence_weight
        if not np.isclose(total, 1.0, atol=1e-5):
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self


class UserGhostProfile(BaseModel):
    """The predictive historical profile of the user."""
    pos_vector: List[float] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    @field_validator("pos_vector")
    def validate_finite_vector(cls, v: List[float]) -> List[float]:
        if not np.isfinite(v).all():
            raise ValueError("Ghost vector contains non-finite values (NaN/Inf).")
        return v


class CognitiveAssessment(BaseModel):
    """The deterministic output payload representing the system's state of mind."""
    uncertainty: float = Field(ge=0.0)
    drift: float = Field(ge=0.0)
    stance: CognitiveStance
    action_directive: ActionDirective
    reason: str
    meta_engine_version: str = "MetaCognition_v2.0"
    historical_confidence: float


# --- CORE SERVICE ---

class MetaCognitionService:
    """
    🧘 THE CONSCIENCE OF THE SYSTEM (Layer 0 - Epistemic Engine).

    Acts as a 'Circuit Breaker' for AI Hallucinations and Overconfidence.
    Evaluates 'Epistemic Uncertainty' by measuring the Euclidean drift
    between the user's historical embedding ('Ghost') and their current session vector.
    """

    def __init__(self, config: Optional[MetaCognitionConfig] = None):
        """
        Initializes the layer via Dependency Injection.
        Does NOT enforce singleton internally to preserve testability and lifecycle control.
        """
        self.config = config or MetaCognitionConfig()

    def evaluate_confidence(
        self,
        ghost_profile: Optional[Dict[str, Any]],
        current_session_vector: List[float]
    ) -> CognitiveAssessment:
        """
        🚀 EPISTEMIC AUDIT: Calculates the state of mind of the AI agent.

        Args:
            ghost_profile: Raw dictionary representing historical predictive profile.
            current_session_vector: The dense embedding of the current intent.

        Returns:
            CognitiveAssessment: Strictly typed output for downstream orchestrators.
        """

        # 🛡️ 1. COLD START GUARD
        if not ghost_profile or not ghost_profile.get('pos') or not current_session_vector:
            return CognitiveAssessment(
                uncertainty=1.0,
                drift=0.0,
                stance=CognitiveStance.INQUISITIVE,
                action_directive=ActionDirective.BROADEN_SEARCH_HORIZON,
                reason="Cold Start / Insufficient historical data",
                historical_confidence=0.0
            )

        try:
            # 🛡️ 2. BOUNDARY VALIDATION
            ghost = UserGhostProfile(
                pos_vector=ghost_profile.get('pos', []),
                confidence=ghost_profile.get('confidence', 0.8)
            )

            # 🧮 3. DIMENSIONALITY & MATH SAFETY
            ghost_arr = np.array(ghost.pos_vector, dtype=np.float32)
            current_arr = np.array(current_session_vector, dtype=np.float32)

            if not np.isfinite(current_arr).all():
                raise ValueError("Current session vector contains non-finite values.")

            if ghost_arr.shape != current_arr.shape:
                logger.warning(
                    "Dimensionality mismatch in epistemic evaluation.",
                    extra={
                        "ghost_dim": ghost_arr.shape,
                        "current_dim": current_arr.shape
                    }
                )
                return self._create_fallback_assessment(reason="Dimension mismatch logic bypass")

            # 🧮 4. THE MATH (Euclidean Drift & Uncertainty Scoring)
            drift_distance = float(np.linalg.norm(ghost_arr - current_arr))

            # Uncertainty = (Drift * W1) + ((1 - Historical_Confidence) * W2)
            uncertainty_score = (drift_distance * self.config.drift_weight) + \
                                ((1.0 - ghost.confidence) * self.config.confidence_weight)

            # 🚦 5. DECISION MATRIX
            stance = CognitiveStance.AUTHORITATIVE
            directive = ActionDirective.COLLAPSE_WAVEFUNCTION
            reason = "Stable Behavior Context"

            if uncertainty_score > self.config.uncertainty_threshold:
                stance = CognitiveStance.INQUISITIVE
                directive = ActionDirective.BROADEN_SEARCH_HORIZON
                reason = f"High Epistemic Uncertainty ({uncertainty_score:.3f})"

            elif drift_distance > self.config.drift_tolerance:
                stance = CognitiveStance.ADAPTIVE_SHOCK
                directive = ActionDirective.TRIGGER_CLARIFICATION
                reason = f"Acute Context Drift Detected ({drift_distance:.3f})"

            # ✅ 6. DETERMINISTIC OUTPUT
            result = CognitiveAssessment(
                uncertainty=round(uncertainty_score, 4),
                drift=round(drift_distance, 4),
                stance=stance,
                action_directive=directive,
                reason=reason,
                historical_confidence=ghost.confidence
            )

            # Log strategic shifts for observability
            if stance != CognitiveStance.AUTHORITATIVE:
                logger.info(
                    "Cognitive stance shifted",
                    extra={"assessment": result.model_dump(mode="json")}
                )

            return result

        except Exception as e:
            # 🛡️ 7. FAIL-OPEN PROTOCOL
            # Guarantees the system never crashes the primary checkout/interaction loop
            # due to a meta-cognition calculation error (e.g., corrupted memory, missing fields).
            logger.error(
                "Critical failure in Meta-Cognition Layer. Defaulting to Fail-Open.",
                exc_info=True,
                extra={"error": str(e)}
            )
            return self._create_fallback_assessment(reason=f"System Error Protection: {str(e)}")

    def _create_fallback_assessment(self, reason: str) -> CognitiveAssessment:
        """Helper to generate a safe, fail-open state deterministically."""
        return CognitiveAssessment(
            uncertainty=0.0,
            drift=0.0,
            stance=CognitiveStance.SAFE_MODE,
            action_directive=ActionDirective.FAIL_OPEN,
            reason=reason,
            historical_confidence=0.0
        )
