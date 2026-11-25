"""One application lock graph for CI and both Docker modes, no daemon needed."""
from pathlib import Path
import json
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[3]

def test_one_canonical_application_lockfile_and_pinned_workspace_manager():
    files=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    locks=[x for x in files if x.endswith('pnpm-lock.yaml')]
    assert locks==['pnpm-lock.yaml']
    assert not (ROOT/'frontend/web/pnpm-workspace.yaml').exists()
    root=json.loads((ROOT/'package.json').read_text())
    app=json.loads((ROOT/'frontend/web/package.json').read_text())
    assert root['private'] is True and root['packageManager']==app['packageManager']=='pnpm@12.6.0'
    lock=(ROOT/'pnpm-lock.yaml').read_text()
    assert '  frontend/web:' in lock and '  .: {}' in lock


def test_docker_uses_root_graph_frozen_install_and_existing_dev_path():
    docker=(ROOT/'frontend/web/Dockerfile').read_text()
    assert 'COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .pnpmfile.cjs ./' in docker
    assert 'pnpm install --frozen-lockfile --ignore-scripts' in docker
    assert '--no-frozen-lockfile' not in docker
    assert 'WORKDIR /workspace/frontend/web' in docker and 'COPY --from=deps /workspace/node_modules /workspace/node_modules' in docker
    for name in ['docker-compose.yml','docker-compose.dev.yml']:
        assert 'context: .\n      dockerfile: frontend/web/Dockerfile' in (ROOT/name).read_text()
    assert './frontend/web:/workspace/frontend/web:delegated' in (ROOT/'docker-compose.dev.yml').read_text()


def test_root_docker_context_is_default_deny_with_web_secret_exclusions():
    ignore=(ROOT/'frontend/web/Dockerfile.dockerignore').read_text().splitlines()
    assert '**' in ignore and '!frontend/web/**' in ignore
    for name in ['frontend/web/node_modules','frontend/web/.next','frontend/web/.env*','frontend/web/.git','frontend/web/.vercel']:
        assert name in ignore
    assert '!backend/api/**' not in ignore and '!secrets/**' not in ignore


def test_isolated_ci_fixture_keeps_all_assertions_with_canonical_workspace_inputs():
    ci=(ROOT/'.github/workflows/frontend-ci.yml').read_text()
    assert 'mkdir -p "$standalone/frontend/web"' in ci
    assert 'cp package.json pnpm-lock.yaml pnpm-workspace.yaml .pnpmfile.cjs' in ci
    for gate in ['pnpm install --frozen-lockfile','exec node scripts/check-security-dependency-contracts.cjs','exec tsc --noEmit','exec jest --coverage=false --runInBand','pnpm --filter airdeliver/apps/web build']:
        assert gate in ci
    assert 'docker build -f frontend/web/Dockerfile --target runner' in ci
