"""Evidence-bound context diagnostics, not a learned confidence estimator.

The previous distance/weight formula was not calibrated on labeled outcomes.
Keep its configuration and DTO vocabulary for compatibility, but never promote
that formula, missing history or corrupted vectors into certainty or permission.
A learned confidence estimator needs a versioned artifact and held-out evaluation.
"""
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger('airdeliver.meta_cognition')


class CognitiveStance(str, Enum):
    AUTHORITATIVE = 'AUTHORITATIVE'  # Legacy wire value, not emitted without a validated estimator.
    INQUISITIVE = 'INQUISITIVE'
    ADAPTIVE_SHOCK = 'ADAPTIVE_SHOCK'
    SAFE_MODE = 'SAFE_MODE'


class ActionDirective(str, Enum):
    COLLAPSE_WAVEFUNCTION = 'COLLAPSE_WAVEFUNCTION'  # Never transaction authorization.
    BROADEN_SEARCH_HORIZON = 'BROADEN_SEARCH_HORIZON'
    TRIGGER_CLARIFICATION = 'TRIGGER_CLARIFICATION'
    FAIL_OPEN = 'FAIL_OPEN'  # Legacy value retained, not emitted on missing evidence.
    USE_VERIFIED_CONTEXT = 'USE_VERIFIED_CONTEXT'


class MetaCognitionConfig(BaseModel):
    """Legacy diagnostic knobs. None is a calibrated decision threshold."""
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid', frozen=True)
    uncertainty_threshold: float = Field(default=.65, ge=0, le=1)
    drift_tolerance: float = Field(default=.8, ge=0)
    drift_weight: float = Field(default=.7, ge=0, le=1)
    confidence_weight: float = Field(default=.3, ge=0, le=1)

    @model_validator(mode='after')
    def validate_weights(self):
        if not np.isclose(self.drift_weight+self.confidence_weight,1.,atol=1e-5):
            raise ValueError('Diagnostic weights must sum to one')
        return self


class UserGhostProfile(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='ignore')
    pos_vector: List[float] = Field(default_factory=list, max_length=4096)
    # No invented historical confidence when the producer supplies none.
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator('pos_vector')
    @classmethod
    def validate_finite_vector(cls,value):
        if not np.isfinite(value).all():
            raise ValueError('Historical vector must be finite')
        return value


class CognitiveAssessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, frozen=True)
    uncertainty: Optional[float] = Field(default=None, ge=0, le=1)
    drift: Optional[float] = Field(default=None, ge=0)
    stance: CognitiveStance = CognitiveStance.SAFE_MODE
    action_directive: ActionDirective = ActionDirective.USE_VERIFIED_CONTEXT
    reason: str
    meta_engine_version: str = 'MetaCognition_v3.0'
    historical_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    state: str = 'unavailable'
    calibrated: bool = False
    transaction_authorized: bool = False
    estimator_version: Optional[str] = None


class MetaCognitionService:
    def __init__(self,config: Optional[MetaCognitionConfig]=None):
        self.config=config or MetaCognitionConfig()

    def unavailable_assessment(self,reason: str='No validated confidence estimator') -> CognitiveAssessment:
        return self._create_fallback_assessment(reason)

    def evaluate_confidence(self,ghost_profile: Optional[Dict[str,Any]],current_session_vector: List[float]) -> CognitiveAssessment:
        """Legacy entrypoint. No calibrated artifact exists, so certainty is unavailable.

        Behavior ghost vectors are learned output-space projections. Their src_dim
        does not prove they inhabit the text query's input embedding space, even
        when array lengths happen to match. Raw distance here would be misleading.
        Do not run an extra embedding solely to call this unavailable estimator.
        """
        return self._create_fallback_assessment('No validated confidence estimator or verified comparable embedding space')

    def _create_fallback_assessment(self,reason: str) -> CognitiveAssessment:
        return CognitiveAssessment(reason=reason)
