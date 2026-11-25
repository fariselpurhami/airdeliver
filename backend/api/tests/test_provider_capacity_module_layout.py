"""Provider domain ownership must preserve old monkeypatch/import identities."""
from importlib import import_module
from pathlib import Path
import hashlib
import pytest
MODULES=['provider_budget','provider_capacity_snapshot','provider_json_diagnostics',
'provider_response_observation','provider_usage_meter','shared_provider_admission',
'paid_turn_admission','capacity_evidence']

@pytest.mark.parametrize('name',MODULES)
def test_old_and_canonical_paths_are_one_module_object(name):
 canonical=import_module('app.services.provider_capacity.'+name)
 legacy=import_module('app.services.'+name)
 assert canonical is legacy
 assert Path(canonical.__file__).parent.name=='provider_capacity'

@pytest.mark.parametrize('name',MODULES)
def test_monkeypatch_through_legacy_import_is_visible_to_canonical_import(name,monkeypatch):
 canonical=import_module('app.services.provider_capacity.'+name)
 legacy=import_module('app.services.'+name)
 sentinel=object()
 monkeypatch.setattr(legacy,'_layout_identity_sentinel',sentinel,raising=False)
 assert canonical._layout_identity_sentinel is sentinel


def test_domain_implementation_bytes_match_pre_move_manifest():
 import json
 root=Path(__file__).resolve().parents[3]
 manifest=json.loads((root/'docs/verification/provider-capacity-layout-v1.json').read_text())
 assert len(manifest['modules'])==len(MODULES)
 for row in manifest['modules']:
  assert hashlib.sha256((root/row['path']).read_bytes()).hexdigest()==row['sha256']
