"""Repository cache hygiene, no app import or owner-data operation."""
from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[3]

def test_approved_generated_cache_manifest_is_exact_and_absent_from_tracking():
    manifest=json.loads((ROOT/'docs/verification/generated-cache-cleanup-v1.json').read_text())
    rows=manifest['removed']
    assert len(rows)==64 and sum(r['bytes'] for r in rows)==780591
    assert sum('__pycache__/' in r['path'] for r in rows)==57
    assert sum(r['path'].startswith('apps/api/hf_cache/') for r in rows)==7
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    for name in tracked:
        assert '__pycache__/' not in name and not name.startswith('backend/api/hf_cache/')
        assert not name.endswith(('.pyc','.pyo','.tsbuildinfo'))
    assert not set(r['path'] for r in rows).intersection(tracked)

def test_generated_paths_are_ignored_even_after_future_local_recreation():
    names=['backend/api/app/__pycache__/main.cpython-313.pyc','backend/api/hf_cache/xet/logs/new.log']
    result=subprocess.run(['git','check-ignore','--no-index',*names],cwd=ROOT,capture_output=True,text=True,check=True)
    assert result.stdout.splitlines()==names

def test_no_runtime_configuration_points_to_removed_cache_tree():
    for relative in ['docker-compose.yml','docker-compose.dev.yml','backend/api/Dockerfile','backend/api/app/core/config.py']:
        content=(ROOT/relative).read_text()
        assert 'backend/api/hf_cache' not in content
    # Application source remains the import authority, not old Python3.11cache.
    assert (ROOT/'backend/api/app/main.py').is_file()
    assert (ROOT/'backend/api/app/services/ai_nlu_service.py').is_file()
