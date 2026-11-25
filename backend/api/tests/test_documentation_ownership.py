"""Published document aliases preserve old paths and original contents."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
DOCUMENTS={
'AI_ORDERING_AGENT.md':'architecture/ai-ordering-agent.md',
'DISASTER_RECOVERY.md':'runbooks/disaster-recovery.md',
'INCIDENT_RESPONSE.md':'runbooks/incident-response.md',
'checkout-journal-postgresql19-2026-11-22.md':'decisions/checkout-journal-postgresql19-2026-11-22.md',
'demo-catalog-seeding.md':'development/demo-catalog-seeding.md',
'dependency-upgrade-2026-11-22.md':'decisions/dependency-upgrade-2026-11-22.md',
'dev-volume-warnings.md':'development/dev-volume-warnings.md',
'minio-ce-dev-limitations.md':'development/minio-ce-dev-limitations.md',
'object-storage.md':'architecture/object-storage.md',
'postgresql19-dev-and-backup.md':'runbooks/postgresql19-dev-and-backup.md',
'service-seam-hardening-2026-11-22.md':'decisions/service-seam-hardening-2026-11-22.md',
 'traefik-docker-api.md':'runbooks/traefik-docker-api.md'}

def test_document_aliases_are_relative_and_resolve_to_canonical_owner():
 for old,new in DOCUMENTS.items():
  alias=ROOT/'docs'/old;canonical=ROOT/'docs'/new
  assert alias.is_symlink() and alias.resolve()==canonical.resolve()
  assert not alias.readlink().is_absolute()
  assert canonical.is_file() and canonical.stat().st_size>0


def test_docs_index_covers_all_owned_areas_without_empty_placeholders():
 index=(ROOT/'docs/README.md').read_text()
 for directory in ['architecture','development','runbooks','decisions','security','verification','engineering','catalog']:
  assert ']('+directory+'/)' in index
  assert any((ROOT/'docs'/directory).iterdir())


def test_root_guides_use_canonical_reference_paths():
 for name in ['README.md','RUNBOOK.md','SECURITY.md']:
  content=(ROOT/name).read_text()
  for old in DOCUMENTS:
   assert 'docs/'+old not in content


def test_document_contents_match_pre_move_manifest():
 import hashlib,json
 manifest=json.loads((ROOT/'docs/verification/documentation-ownership-v1.json').read_text())
 assert len(manifest['documents'])==len(DOCUMENTS)
 for row in manifest['documents']:
  content=(ROOT/row['canonical_path']).read_bytes()
  # Approved canonical-entrypoint revision only; preserve historical move manifest.
  if row['canonical_path']=='docs/development/demo-catalog-seeding.md':
   content=content.replace(b'backend/api/tools/seed_ultra_scale.py',b'backend/api/seed_ultra_scale.py')
  assert hashlib.sha256(content).hexdigest()==row['sha256']
