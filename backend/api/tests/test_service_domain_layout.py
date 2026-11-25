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
 assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['canonical_sha256']


def test_voice_foundation_stays_at_its_existing_path():
 assert (ROOT/'backend/api/app/services/ai_voice_service.py').is_file()
 assert 'class AIVoiceOrchestrator' in (ROOT/'backend/api/app/services/ai_voice_service.py').read_text()


def test_payment_logger_routes_remain_historical():
 for name in ['payment_completion_service','payment_outbox_service']:
  module=import_module('app.services.'+name)
  assert module.logger.name=='app.services.'+name
