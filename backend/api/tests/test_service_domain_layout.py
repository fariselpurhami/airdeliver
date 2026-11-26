"""Domain moves retain legacy imports, shared state and source provenance."""
from importlib import import_module
from pathlib import Path
import hashlib
import json
import pytest
ROOT=Path(__file__).resolve().parents[3]
MANIFEST=json.loads((ROOT/'docs/verification/service-domain-layout-v1.json').read_text())

@pytest.mark.parametrize('row',MANIFEST['modules'],ids=lambda row:row['legacy_module'])
def test_legacy_and_domain_imports_share_one_module_and_state(row,monkeypatch):
 legacy=import_module(row['legacy_module']);canonical=import_module(row['canonical_module'])
 assert legacy is canonical
 sentinel=object();monkeypatch.setattr(legacy,'_layout_test_sentinel',sentinel,raising=False)
 assert canonical._layout_test_sentinel is sentinel
 source=(ROOT/row['path']).read_bytes()
 # Preserve the immutable move manifest while accounting for the separately
 # approved canonical maintenance import after root CLI wrapper retirement.
 if row['canonical_module']=='app.services.catalog.real_catalog_import':
  assert b'from tools.seed_ultra_scale import ProductVector' in source
  source=source.replace(b'from tools.seed_ultra_scale import ProductVector',b'from seed_ultra_scale import ProductVector')
 evolution=json.loads((ROOT/'docs/verification/conversation-security-evolution-v1.json').read_text())
 assert set(evolution)=={'backend/api/app/services/conversation/free_llm_service.py'}
 logging_evolution=json.loads((ROOT/'docs/verification/raw-logging-source-evolution-v1.json').read_text())['modules']
 expected=logging_evolution[row['path']]['current_sha256'] if row['path'] in logging_evolution else evolution.get(row['path'],row['canonical_sha256'])
 writer=json.loads((ROOT/'docs/verification/writer-fact-binding-source-evolution-v1.json').read_text())
 assert set(writer)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in writer:
  assert writer[row['path']]['baseline_sha256']==expected
  expected=writer[row['path']]['current_sha256']
 atomic=json.loads((ROOT/'docs/verification/support-session-source-evolution-v1.json').read_text())
 assert set(atomic)=={'backend/api/app/services/conversation/neural_core_service.py'}
 if row['path'] in atomic:
  assert atomic[row['path']]['baseline_sha256']==expected
  expected=atomic[row['path']]['current_sha256']
 budget=json.loads((ROOT/'docs/verification/legacy-intent-budget-source-evolution-v1.json').read_text())
 assert set(budget)=={'backend/api/app/services/conversation/ai_nlu_service.py'}
 if row['path'] in budget:
  assert budget[row['path']]['baseline_sha256']==expected
  expected=budget[row['path']]['current_sha256']
 gw=json.loads((ROOT/'docs/verification/worker-gateway-log-source-evolution-v1.json').read_text())
 assert set(gw)=={'backend/api/app/services/orchestration/worker_entrypoint.py'}
 if row['path'] in gw:
  assert gw[row['path']]['baseline_sha256']==expected
  expected=gw[row['path']]['current_sha256']
 truth=json.loads((ROOT/'docs/verification/product-truth-source-evolution-v1.json').read_text())['modules']
 if row['path'] in truth:
  assert truth[row['path']]['previous_sha256']==expected
  expected=truth[row['path']]['current_sha256']
 wr=json.loads((ROOT/'docs/verification/withheld-reason-source-evolution-v1.json').read_text())
 assert set(wr)=={'backend/api/app/services/conversation/free_llm_service.py'}
 if row['path'] in wr:
  assert wr[row['path']]['baseline_sha256']==expected
  expected=wr[row['path']]['current_sha256']
 cf=json.loads((ROOT/'docs/verification/catalog-fact-answer-source-evolution-v1.json').read_text())
 assert set(cf)=={'backend/api/app/services/conversation/sales_response_service.py'}
 if row['path'] in cf:
  edited=source.decode()
  for edit in cf[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==cf[row['path']]['baseline_sha256']==expected
  expected=cf[row['path']]['current_sha256']
 ns=json.loads((ROOT/'docs/verification/no-stock-phrase-source-evolution-v1.json').read_text())
 assert set(ns)=={'backend/api/app/services/conversation/compact_copy_contracts.py'}
 if row['path'] in ns:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==ns[row['path']]['current_sha256']
  edited=source.decode()
  for edit in ns[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==ns[row['path']]['baseline_sha256']
  source=edited.encode()
 ni=json.loads((ROOT/'docs/verification/no-internal-ids-source-evolution-v1.json').read_text())
 assert set(ni)=={'backend/api/app/services/conversation/compact_copy_contracts.py'}
 if row['path'] in ni:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==ni[row['path']]['current_sha256']
  edited=source.decode()
  for edit in ni[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==ni[row['path']]['baseline_sha256']
  source=edited.encode()
 nio=json.loads((ROOT/'docs/verification/no-invented-offers-source-evolution-v1.json').read_text())
 assert set(nio)=={'backend/api/app/services/conversation/compact_copy_contracts.py'}
 if row['path'] in nio:
  # Newest receipt: verify the live file, then revert it so the older receipts verify the previous state.
  assert hashlib.sha256(source).hexdigest()==nio[row['path']]['current_sha256']
  edited=source.decode()
  for edit in nio[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==nio[row['path']]['baseline_sha256']
  source=edited.encode()
 lr=json.loads((ROOT/'docs/verification/writer-low-reasoning-source-evolution-v1.json').read_text())
 assert set(lr)=={'backend/api/app/services/conversation/free_llm_service.py'}
 if row['path'] in lr:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==lr[row['path']]['current_sha256']
  edited=source.decode()
  for edit in lr[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==lr[row['path']]['baseline_sha256']
  source=edited.encode()
 su=json.loads((ROOT/'docs/verification/stock-tell-unicode-source-evolution-v1.json').read_text())
 assert set(su)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in su:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==su[row['path']]['current_sha256']
  edited=source.decode()
  for edit in su[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==su[row['path']]['baseline_sha256']
  source=edited.encode()
 fx=json.loads((ROOT/'docs/verification/voice-repair-four-phase-source-evolution-v1.json').read_text())
 assert set(fx)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in fx:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==fx[row['path']]['current_sha256']
  edited=source.decode()
  for edit in fx[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==fx[row['path']]['baseline_sha256']
  source=edited.encode()
 vx=json.loads((ROOT/'docs/verification/voice-repair-source-evolution-v1.json').read_text())
 assert set(vx)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in vx:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==vx[row['path']]['current_sha256']
  edited=source.decode()
  for edit in vx[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==vx[row['path']]['baseline_sha256']
  source=edited.encode()
 px=json.loads((ROOT/'docs/verification/asked-terms-neutral-policy-source-evolution-v1.json').read_text())
 assert set(px)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in px:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==px[row['path']]['current_sha256']
  edited=source.decode()
  for edit in px[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==px[row['path']]['baseline_sha256']
  source=edited.encode()
 dx=json.loads((ROOT/'docs/verification/sole-named-card-source-evolution-v1.json').read_text())
 assert set(dx)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in dx:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==dx[row['path']]['current_sha256']
  edited=source.decode()
  for edit in dx[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==dx[row['path']]['baseline_sha256']
  source=edited.encode()
 sx=json.loads((ROOT/'docs/verification/stock-claim-completion-source-evolution-v1.json').read_text())
 assert set(sx)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in sx:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==sx[row['path']]['current_sha256']
  edited=source.decode()
  for edit in sx[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==sx[row['path']]['baseline_sha256']
  source=edited.encode()
 ax=json.loads((ROOT/'docs/verification/asked-unlisted-source-evolution-v1.json').read_text())
 assert set(ax)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in ax:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==ax[row['path']]['current_sha256']
  edited=source.decode()
  for edit in ax[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==ax[row['path']]['baseline_sha256']
  source=edited.encode()
 nx=json.loads((ROOT/'docs/verification/no-indication-source-evolution-v1.json').read_text())
 assert set(nx)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in nx:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==nx[row['path']]['current_sha256']
  edited=source.decode()
  for edit in nx[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==nx[row['path']]['baseline_sha256']
  source=edited.encode()
 cu=json.loads((ROOT/'docs/verification/colon-unknown-source-evolution-v1.json').read_text())
 assert set(cu)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in cu:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==cu[row['path']]['current_sha256']
  edited=source.decode()
  for edit in cu[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==cu[row['path']]['baseline_sha256']
  source=edited.encode()
 et=json.loads((ROOT/'docs/verification/exact-totals-source-evolution-v1.json').read_text())
 assert set(et)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in et:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==et[row['path']]['current_sha256']
  edited=source.decode()
  for edit in et[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==et[row['path']]['baseline_sha256']
  source=edited.encode()
 np=json.loads((ROOT/'docs/verification/negated-promise-source-evolution-v1.json').read_text())
 assert set(np)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in np:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==np[row['path']]['current_sha256']
  edited=source.decode()
  for edit in np[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==np[row['path']]['baseline_sha256']
  source=edited.encode()
 nc=json.loads((ROOT/'docs/verification/name-claim-completion-source-evolution-v1.json').read_text())
 assert set(nc)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in nc:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==nc[row['path']]['current_sha256']
  edited=source.decode()
  for edit in nc[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==nc[row['path']]['baseline_sha256']
  source=edited.encode()
 be=json.loads((ROOT/'docs/verification/writer-budget-echo-source-evolution-v1.json').read_text())
 assert set(be)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in be:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==be[row['path']]['current_sha256']
  edited=source.decode()
  for edit in be[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==be[row['path']]['baseline_sha256']
  source=edited.encode()
 cn=json.loads((ROOT/'docs/verification/writer-coordinated-negation-source-evolution-v1.json').read_text())
 assert set(cn)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in cn:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==cn[row['path']]['current_sha256']
  edited=source.decode()
  for edit in cn[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==cn[row['path']]['baseline_sha256']
  source=edited.encode()
 nv=json.loads((ROOT/'docs/verification/writer-number-value-source-evolution-v1.json').read_text())
 assert set(nv)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in nv:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==nv[row['path']]['current_sha256']
  edited=source.decode()
  for edit in nv[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==nv[row['path']]['baseline_sha256']
  source=edited.encode()
 vr=json.loads((ROOT/'docs/verification/validator-reason-log-source-evolution-v1.json').read_text())
 assert set(vr)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in vr:
  # Newest receipt: verify the live file, then revert it so older receipts verify the prior stage.
  assert hashlib.sha256(source).hexdigest()==vr[row['path']]['current_sha256']
  edited=source.decode()
  for edit in vr[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==vr[row['path']]['baseline_sha256']
  source=edited.encode()
 ng=json.loads((ROOT/'docs/verification/negated-policy-source-evolution-v1.json').read_text())
 assert set(ng)=={'backend/api/app/services/conversation/shopping_copy.py'}
 if row['path'] in ng:
  edited=source.decode()
  for edit in ng[row['path']]['replacements']:
   assert edited.count(edit['new'])==edit['count']
   edited=edited.replace(edit['new'],edit['old'])
  assert hashlib.sha256(edited.encode()).hexdigest()==ng[row['path']]['baseline_sha256']==expected
  expected=ng[row['path']]['current_sha256']
 assert hashlib.sha256(source).hexdigest()==expected


def test_voice_foundation_stays_at_its_existing_path():
 assert (ROOT/'backend/api/app/services/ai_voice_service.py').is_file()
 assert 'class AIVoiceOrchestrator' in (ROOT/'backend/api/app/services/ai_voice_service.py').read_text()


def test_payment_logger_routes_remain_historical():
 for name in ['payment_completion_service','payment_outbox_service']:
  module=import_module('app.services.'+name)
  assert module.logger.name=='app.services.'+name
