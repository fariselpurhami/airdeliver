"""Maintenance relocation is verified without executing dangerous helpers."""
from pathlib import Path
import ast
import hashlib
import json
import runpy
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[3]
API=ROOT/'backend/api'
MANIFEST=json.loads((ROOT/'docs/verification/api-tool-layout-v1.json').read_text())

@pytest.mark.parametrize('row',MANIFEST['tools'],ids=lambda row:Path(row['legacy_path']).stem)
def test_tool_content_and_wrappers_are_explicit_without_running_implementation(row):
 legacy=ROOT/row['legacy_path'];canonical=ROOT/row['canonical_path']
 assert hashlib.sha256(canonical.read_bytes()).hexdigest()==row['canonical_sha256']
 tree=ast.parse(legacy.read_text())
 assert any(isinstance(n,ast.If) for n in tree.body)
 assert "run_name='__main__'" in legacy.read_text()
 assert "_sys.modules[__name__]" in legacy.read_text()


@pytest.mark.parametrize('name',['create_db','create_db_and_tables','fix_milvus','hash_password','init_data','nuke_milvus_v2','reset_db','seed_ultra_scale','sync_search'])
def test_legacy_cli_forwards_main_without_importing_real_tool(name,monkeypatch):
 calls=[]
 monkeypatch.setattr(runpy,'run_module',lambda *a,**kw:calls.append((a,kw)))
 runpy.run_path(str(API/(name+'.py')),run_name='__main__')
 assert calls==[(('tools.'+name,),{'run_name':'__main__'})]


def test_seed_tool_legacy_import_keeps_module_identity():
 import seed_ultra_scale
 from tools import seed_ultra_scale as canonical
 assert seed_ultra_scale is canonical


def test_file_relative_semantics_preserved_not_silently_fixed():
 assert (API/'tools/create_db.py').parent.parent==API
 # Original expression API/create_db_and_tables.py -> API.parent/app/models.
 assert (API/'tools/create_db_and_tables.py').parents[2]/'app' == API.parent/'app'
