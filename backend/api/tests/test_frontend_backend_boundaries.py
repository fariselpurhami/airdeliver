"""Canonical app ownership and compatibility without duplicate source trees."""
from pathlib import Path
import json
import subprocess
ROOT=Path(__file__).resolve().parents[3]

def test_canonical_apps_and_relative_compatibility_aliases():
    assert (ROOT/'frontend/web/package.json').is_file()
    assert (ROOT/'backend/api/pyproject.toml').is_file()
    for alias,target in [('apps/web','frontend/web'),('apps/api','backend/api')]:
        p=ROOT/alias
        assert p.is_symlink() and p.resolve()==(ROOT/target).resolve()
        assert not str(p.readlink()).startswith('/')
    assert json.loads((ROOT/'frontend/web/package.json').read_text())['name']=='airdeliver/apps/web'


def test_workspace_discovers_each_package_once_not_through_aliases():
    config=(ROOT/'pnpm-workspace.yaml').read_text()
    assert '"frontend/*"' in config and '"backend/*"' in config
    assert '"apps/*"' not in config
    assert '  frontend/web:' in (ROOT/'pnpm-lock.yaml').read_text()


def test_build_and_development_interfaces_preserve_container_paths():
    docker=(ROOT/'frontend/web/Dockerfile').read_text()
    assert 'WORKDIR /app' in docker and 'WORKDIR /app/frontend/web' in docker
    assert '/workspace/frontend/web/.next/standalone' in docker
    ignore=(ROOT/'frontend/web/Dockerfile.dockerignore').read_text()
    assert '!frontend/' in ignore and '!frontend/web/**' in ignore
    assert 'frontend/web/.env*' in ignore
    for name in ['docker-compose.yml','docker-compose.dev.yml']:
        s=(ROOT/name).read_text()
        assert 'context: ./backend/api' in s
        assert 'dockerfile: frontend/web/Dockerfile' in s
    assert './frontend/web:/app:delegated' in (ROOT/'docker-compose.dev.yml').read_text()


def test_old_directory_cli_resolves_the_same_sources_without_copying():
    assert (ROOT/'apps/api/app/main.py').samefile(ROOT/'backend/api/app/main.py')
    assert (ROOT/'apps/web/package.json').samefile(ROOT/'frontend/web/package.json')
    result=subprocess.run(['make','--dry-run','up'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert 'docker-compose.yml -f docker-compose.dev.yml' in result.stdout


def test_historical_fixture_bindings_and_scan_fingerprints_keep_original_paths():
    # The cleanup manifest proves historical deletions, not current ownership.
    manifest=(ROOT/'docs/verification/generated-cache-cleanup-v1.json').read_text()
    assert 'apps/api/hf_cache' in manifest
    fingerprints=(ROOT/'.gitleaksignore').read_text()
    assert ':apps/api/' in fingerprints
    assert ':backend/api/' not in fingerprints
