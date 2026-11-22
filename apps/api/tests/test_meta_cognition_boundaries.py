"""Uncalibrated distance is diagnostic, never transaction/confidence authority."""
import math
import numpy as np
import pytest
from pydantic import ValidationError
from app.services.ai_meta_cognition import MetaCognitionConfig,MetaCognitionService,ActionDirective,CognitiveStance

@pytest.mark.parametrize('ghost,current',[
    (None,[1.,0.]), ({'pos':[1.,0.]},[1.,0.]),
    ({'pos':[1.,0.],'confidence':.99},[1.,0.]),
    ({'pos':[0.,0.]},[0.,0.]), ({'pos':[1.,0.]},[float('nan'),0.]),
    ({'pos':[1.,0.]},[1.]), ({'pos':[1e308,0.]},[-1e308,0.]),
    ({'pos':np.array([1.,0.])},np.array([1.,0.])),
])
def test_unvalidated_inputs_never_produce_authority_or_false_zero_uncertainty(ghost,current):
    result=MetaCognitionService().evaluate_confidence(ghost,current)
    assert result.stance==CognitiveStance.SAFE_MODE
    assert result.action_directive!=ActionDirective.COLLAPSE_WAVEFUNCTION
    assert result.uncertainty is None and result.historical_confidence is None
    assert result.calibrated is False and result.transaction_authorized is False


def test_same_dimension_is_not_same_embedding_space():
    result=MetaCognitionService().evaluate_confidence({'pos':[1.,0.],'model_id':'learned-ghost-output'},[1.,0.])
    assert result.drift is None
    assert result.state=='unavailable'


def test_config_rejects_nonfinite_hyperparameters():
    with pytest.raises(ValidationError):
        MetaCognitionConfig(drift_tolerance=math.inf)
