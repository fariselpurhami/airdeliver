"""Feature/experiment foundations must be explicit and stable, not live claims."""
import pytest
from app.services.feature_flags import FeatureFlags
from app.services.experimentation_service import ExperimentationService


def test_legacy_boolean_flag_does_not_crash():
    assert FeatureFlags().is_enabled('ai-chatbot-enabled',1) is True


@pytest.mark.parametrize('user',[True,False,0,-1,1.5,'12',None])
def test_invalid_identity_cannot_enter_rollout(user):
    assert FeatureFlags().is_enabled('new-checkout-flow',user) is False


def test_unknown_flag_is_disabled():
    assert FeatureFlags().is_enabled('unregistered',1) is False


def test_explicit_rollout_is_stable_and_namespaced():
    flags=FeatureFlags({'a':(False,50),'b':(False,50)})
    one=[flags.is_enabled('a',i) for i in range(1,1001)]
    assert one==[FeatureFlags({'a':(False,50)}).is_enabled('a',i) for i in range(1,1001)]
    assert 350<sum(one)<650
    assert one!=[flags.is_enabled('b',i) for i in range(1,1001)]


@pytest.mark.parametrize('value',[(False,101),(False,-1),(True,float('nan')),(False,1.5),'enabled'])
def test_invalid_rollout_config_is_rejected(value):
    with pytest.raises(ValueError):FeatureFlags({'flag':value})


def test_experiment_requires_explicit_assignment_and_records_version():
    exp=ExperimentationService(experiments={'checkout':{'version':'v1','variants':['blue','green']}})
    assignment=exp.get_assignment(25,'checkout')
    assert assignment.variant in {'blue','green'} and assignment.version=='v1'
    assert assignment==exp.get_assignment(25,'checkout')
    assert exp.get_user_variant(25,'unknown')=='control'
    assert exp.get_user_variant(True,'checkout')=='control'
    assert exp.get_assignment(1,'unknown').assigned is False


def test_no_unconfigured_live_experiments():
    assert ExperimentationService().get_user_variant(25,'checkout-button-color')=='control'
