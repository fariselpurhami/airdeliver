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
 assert hashlib.sha256(source).hexdigest()==expected


def test_voice_foundation_stays_at_its_existing_path():
 assert (ROOT/'backend/api/app/services/ai_voice_service.py').is_file()
 assert 'class AIVoiceOrchestrator' in (ROOT/'backend/api/app/services/ai_voice_service.py').read_text()


def test_payment_logger_routes_remain_historical():
 for name in ['payment_completion_service','payment_outbox_service']:
  module=import_module('app.services.'+name)
  assert module.logger.name=='app.services.'+name
