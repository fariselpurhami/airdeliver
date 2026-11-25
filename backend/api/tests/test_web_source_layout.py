"""Next source ownership preserves every implementation byte and route boundary."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]
WEB=ROOT/'frontend/web'

def test_source_manifest_preserves_every_pre_move_byte():
 manifest=json.loads((ROOT/'docs/verification/web-source-layout-v1.json').read_text())
 assert len(manifest['files'])>100
 for row in manifest['files']:
  assert not (ROOT/row['previous_path']).exists()
  assert hashlib.sha256((ROOT/row['canonical_path']).read_bytes()).hexdigest()==row['sha256']


def test_next_source_has_one_app_and_proxy_boundary_not_duplicate_route_symlinks():
 assert (WEB/'src/app').is_dir() and (WEB/'src/proxy.ts').is_file()
 for old in ['app','proxy.ts','auth.ts','components','hooks','lib','types']:
  assert not (WEB/old).exists() and not (WEB/old).is_symlink()
 for name in ['public','next.config.mjs','package.json','tsconfig.json']:
  assert (WEB/name).exists()


def test_source_aliases_shadcn_and_coverage_point_at_canonical_source():
 assert '"./src/*"' in (WEB/'tsconfig.json').read_text()
 assert json.loads((WEB/'components.json').read_text())['tailwind']['css']=='src/app/globals.css'
 jest=(WEB/'jest.config.mjs').read_text()
 for folder in ['app','components','lib']:assert "'src/"+folder+"/**/*" in jest
 assert './src/**/*' in (WEB/'tailwind.config.ts').read_text()
