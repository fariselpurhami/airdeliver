"""Canonical maintenance ownership, no dangerous helper execution."""
from pathlib import Path
import ast
import hashlib
import json
import pytest
ROOT=Path(__file__).resolve().parents[3]
API=ROOT/'backend/api'
MANIFEST=json.loads((ROOT/'docs/verification/api-tool-layout-v1.json').read_text())

@pytest.mark.parametrize('row',MANIFEST['tools'],ids=lambda row:Path(row['legacy_path']).stem)
def test_tool_implementations_retained_but_approved_root_wrappers_removed(row):
 legacy=ROOT/row['legacy_path'];canonical=ROOT/row['canonical_path']
 assert not legacy.exists()
 # init_data import was redirected to the canonical seeder; all other bodies unchanged.
 content=canonical.read_bytes()
 if canonical.name=='init_data.py':content=content.replace(b'from tools.seed_ultra_scale import',b'from seed_ultra_scale import')
 assert hashlib.sha256(content).hexdigest()==row['canonical_sha256']
 ast.parse(canonical.read_text())


def test_seed_canonical_import_and_file_relative_semantics():
 from tools import seed_ultra_scale as seed
 assert Path(seed.__file__).parent==API/'tools'
 assert (API/'tools/create_db.py').parent.parent==API
 assert (API/'tools/create_db_and_tables.py').parents[2]/'app'==API.parent/'app'
