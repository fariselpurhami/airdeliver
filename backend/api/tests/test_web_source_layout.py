"""Next source ownership preserves every implementation byte and route boundary."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]
WEB=ROOT/'frontend/web'

def test_source_manifest_preserves_every_pre_move_byte():
 manifest=json.loads((ROOT/'docs/verification/web-source-layout-v1.json').read_text())
 evolution=json.loads((ROOT/'docs/verification/web-source-evolution-v1.json').read_text())
 assert set(evolution)=={'frontend/web/src/app/globals.css','frontend/web/src/app/(main)/_components/LandingClient.tsx','frontend/web/src/components/layout/Header.tsx','frontend/web/src/components/ai/Chatbot.tsx'}
 assert len(manifest['files'])>100
 for row in manifest['files']:
  assert not (ROOT/row['previous_path']).exists()
  assert hashlib.sha256((ROOT/row['canonical_path']).read_bytes()).hexdigest()==evolution.get(row['canonical_path'],row['sha256'])


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


def test_reviewed_source_evolution_does_not_rewrite_historical_move_manifest():
 manifest=json.loads((ROOT/'docs/verification/web-source-layout-v1.json').read_text())
 evolution=json.loads((ROOT/'docs/verification/web-source-evolution-v1.json').read_text())
 historical={row['canonical_path']:row['sha256'] for row in manifest['files']}
 for name,digest in evolution.items():
  assert name in historical and digest!=historical[name]
  assert len(digest)==64
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
