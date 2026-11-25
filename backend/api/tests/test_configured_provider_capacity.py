"""Configuration readiness only. No subscription, account or provider action."""
import pytest
from pydantic import ValidationError
from app.core.config import CoreSettings

FIELDS=['PROVIDER_CAPACITY_PLAN','PROVIDER_PLAN_TPM_LIMIT','PROVIDER_TPM_HEADROOM_PERCENT','PROVIDER_TPM_BUDGET']
@pytest.fixture
def settings(monkeypatch):
 for f in FIELDS:monkeypatch.delenv(f,raising=False)
 return lambda **kw:CoreSettings(_env_file=None,**kw)
def test_default_free_capacity_unchanged(settings):
 s=settings();assert s.PROVIDER_CAPACITY_PLAN=='free' and s.PROVIDER_PLAN_TPM_LIMIT==8000 and s.PROVIDER_TPM_BUDGET==7200
@pytest.mark.parametrize('values,expected',[
 ({'PROVIDER_CAPACITY_PLAN':'developer'},225000),
 ({'PROVIDER_CAPACITY_PLAN':'developer','PROVIDER_PLAN_TPM_LIMIT':100000},90000),
 ({'PROVIDER_CAPACITY_PLAN':'custom','PROVIDER_PLAN_TPM_LIMIT':50000},45000),
 ({'PROVIDER_TPM_BUDGET':5000},5000),
 ({'PROVIDER_CAPACITY_PLAN':'developer','PROVIDER_TPM_BUDGET':7200},7200),
])
def test_explicit_plan_and_org_limits_derive_safe_local_budget(settings,values,expected):assert settings(**values).PROVIDER_TPM_BUDGET==expected
@pytest.mark.parametrize('values',[
 {'PROVIDER_CAPACITY_PLAN':'custom'}, {'PROVIDER_PLAN_TPM_LIMIT':250000},
 {'PROVIDER_TPM_BUDGET':8000},{'PROVIDER_CAPACITY_PLAN':'developer','PROVIDER_TPM_BUDGET':250000},
 {'PROVIDER_TPM_HEADROOM_PERCENT':51},{'PROVIDER_CAPACITY_PLAN':'invented'},
])
def test_conflicting_or_unverified_configuration_fails_closed(settings,values):
 with pytest.raises(ValidationError):settings(**values)


@pytest.mark.asyncio
async def test_plan_budget_reaches_actual_shared_ledger_without_live_provider(settings,monkeypatch):
 from types import SimpleNamespace
 from app.services.shared_provider_admission import shared_provider_slot,SharedProviderBudgetError,provider_turn_budget
 free=settings();paid=settings(PROVIDER_CAPACITY_PLAN='developer')
 class Client:
  def __init__(self):self.calls=[]
  async def eval(self,*args):self.calls.append(args);return 1
  async def aclose(self):pass
 client=Client()
 monkeypatch.setattr('app.core.config.get_core_settings',lambda:free)
 with pytest.raises(SharedProviderBudgetError):
  async with shared_provider_slot('offline-plan',[],{},8000,client=client):pytest.fail('free should withhold')
 assert client.calls==[]
 monkeypatch.setattr('app.core.config.get_core_settings',lambda:paid)
 # This isolated ledger test supplies an explicit offline transport; fairness
 # is covered separately with a real Redis client and resolved settings.
 from contextlib import asynccontextmanager
 @asynccontextmanager
 async def offline_fairness(*args,**kwargs):yield
 monkeypatch.setattr('app.services.paid_turn_admission.paid_turn_slot',offline_fairness)
 async with shared_provider_slot('offline-plan',[],{},8000,client=client):pass
 assert client.calls[0][1]==15
 assert client.calls[0][20]==225000
 # Changing plan never expands the independent six-call/16000turn bound.
 client.calls.clear()
 async with provider_turn_budget():
  async with shared_provider_slot('offline-plan',[],{},8000,client=client):pass
  with pytest.raises(SharedProviderBudgetError,match='turn_budget_exhausted'):
   async with shared_provider_slot('offline-plan',[],{},8000,client=client):pytest.fail('turn bound retained')
