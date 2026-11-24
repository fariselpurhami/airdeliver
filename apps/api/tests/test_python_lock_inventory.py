import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('lock_inventory', ROOT/'scripts/python_lock_inventory.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_exact_lock_identities_include_platform_variants_and_hashes():
    result=module.inventory(ROOT/'apps/api/poetry.lock')
    identities={(c['name'],c['version']) for c in result['components']}
    assert ('torch','2.15.0+cpu') in identities and ('torch','2.15.0') in identities
    batches=module.batches(result['components'])
    assert len(batches)>=2
    restored={(name,version) for batch in batches for name,version in batch.items()}
    assert restored=={(c['name'],c['version']) for c in result['components'] if c['audit_requirement_eligible']}
    assert all(c['hashes'] and c['license_status']=='not_collected_requires_review' for c in result['components'])


def test_bad_lock_version_cannot_become_a_requirement_option(tmp_path):
    path=tmp_path/'lock'
    path.write_text('[[package]]\nname="example"\nversion="1.0 --index-url malicious"\n')
    with pytest.raises(ValueError):module.inventory(path)


def test_remote_credentials_and_urls_are_not_copied_to_inventory(tmp_path):
    path=tmp_path/'lock'
    path.write_text('[[package]]\nname="example"\nversion="1.0"\n[package.source]\ntype="git"\nurl="https://secret-user:secret-pass@private.invalid/repo"\n')
    result=module.inventory(path)
    import json
    assert 'secret' not in json.dumps(result)
    assert module.batches(result['components'])==[]
