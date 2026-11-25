from pathlib import Path
import hashlib
import json
import ast
ROOT=Path(__file__).resolve().parents[3]

def test_worker_is_byte_identical_at_owner_selected_services_domain():
 manifest=json.loads((ROOT/'docs/verification/canonical-api-entrypoints-v1.json').read_text())
 assert hashlib.sha256((ROOT/manifest['worker_path']).read_bytes()).hexdigest()==manifest['worker_sha256']
 assert not (ROOT/'backend/api/worker_entrypoint.py').exists()
 for old in manifest['removed']:assert not (ROOT/old).exists()
 config=manifest['retained_unique_config']
 assert hashlib.sha256((ROOT/config['path']).read_bytes()).hexdigest()==config['sha256']


def test_compose_and_kubernetes_invoke_canonical_worker_and_seed_modules():
 for name in ['docker-compose.yml','docker-compose.dev.yml','infra/k8s/05-api-worker.yml']:
  s=(ROOT/name).read_text()
  assert 'app.services.orchestration.worker_entrypoint' in s
  assert '/app/worker_entrypoint.py' not in s
 assert '-m tools.seed_ultra_scale' in (ROOT/'docker-compose.dev.yml').read_text()


def test_active_python_sources_do_not_import_deleted_root_interfaces():
 for p in (ROOT/'backend/api').rglob('*.py'):
  for n in ast.walk(ast.parse(p.read_text())):
   if isinstance(n,ast.ImportFrom):assert n.module not in {'worker_entrypoint','seed_ultra_scale'},str(p)
   if isinstance(n,ast.Import):assert not {'worker_entrypoint','seed_ultra_scale'}&{a.name for a in n.names},str(p)
