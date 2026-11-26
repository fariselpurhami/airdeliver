"""Next source ownership preserves every implementation byte and route boundary."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[3]
WEB=ROOT/'frontend/web'

def test_source_manifest_preserves_every_pre_move_byte():
 manifest=json.loads((ROOT/'docs/verification/web-source-layout-v1.json').read_text())
 evolution=json.loads((ROOT/'docs/verification/web-source-evolution-v1.json').read_text())
 assert set(evolution)=={'frontend/web/src/app/globals.css','frontend/web/src/app/(main)/_components/LandingClient.tsx','frontend/web/src/components/layout/Header.tsx','frontend/web/src/components/ai/Chatbot.tsx','frontend/web/src/app/(main)/products/page.tsx'}
 assert len(manifest['files'])>100
 security=json.loads((ROOT/'docs/verification/next-security-source-evolution-v1.json').read_text())
 reset=json.loads((ROOT/'docs/verification/support-reset-source-evolution-v1.json').read_text())
 assert set(reset)=={'frontend/web/src/hooks/useAIOrderingStore.ts'}
 ui=json.loads((ROOT/'docs/verification/web-ui-source-evolution-v1.json').read_text())
 for row in manifest['files']:
  assert not (ROOT/row['previous_path']).exists()
  expected=security[row['canonical_path']]['current_sha256'] if row['canonical_path'] in security else evolution.get(row['canonical_path'],row['sha256'])
  if row['canonical_path'] in reset:
   assert reset[row['canonical_path']]['baseline_sha256']==expected
   expected=reset[row['canonical_path']]['current_sha256']
  if row['canonical_path'] in ui:
   assert ui[row['canonical_path']]['baseline_sha256']==expected
   expected=ui[row['canonical_path']]['current_sha256']
  assert hashlib.sha256((ROOT/row['canonical_path']).read_bytes()).hexdigest()==expected


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
 ui=json.loads((ROOT/'docs/verification/web-ui-source-evolution-v1.json').read_text())
 for name,digest in evolution.items():
  assert name in historical and digest!=historical[name]
  assert len(digest)==64
  expected=digest
  if name in ui:
   assert ui[name]['baseline_sha256']==digest
   expected=ui[name]['current_sha256']
  assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected


def test_next_security_evolution_has_exact_current_hashes_and_keeps_move_receipts():
 security=json.loads((ROOT/'docs/verification/next-security-source-evolution-v1.json').read_text())
 assert len(security)==9
 for path,row in security.items():
  expected=row['current_sha256']
  later=json.loads((ROOT/'docs/verification/web-ui-source-evolution-v1.json').read_text()).get(path)
  if later:
   assert later['baseline_sha256']==expected
   expected=later['current_sha256']
  assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected
  assert row['baseline_sha256'] is None or len(row['baseline_sha256'])==64
