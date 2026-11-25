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
    assert not (ROOT/'apps/web/pnpm-workspace.yaml').exists()
    root=json.loads((ROOT/'package.json').read_text())
    app=json.loads((ROOT/'apps/web/package.json').read_text())
    assert root['private'] is True and root['packageManager']==app['packageManager']=='pnpm@12.6.0'
    lock=(ROOT/'pnpm-lock.yaml').read_text()
    assert '  apps/web:' in lock and '  .: {}' in lock


def test_docker_uses_root_graph_frozen_install_and_existing_dev_path():
    docker=(ROOT/'apps/web/Dockerfile').read_text()
    assert 'COPY pnpm-lock.yaml pnpm-workspace.yaml .pnpmfile.cjs ./' in docker
    assert 'pnpm install --frozen-lockfile --ignore-scripts' in docker
    assert '--no-frozen-lockfile' not in docker
    assert 'WORKDIR /app' in docker and 'COPY --from=deps /workspace/node_modules /node_modules' in docker
    for name in ['docker-compose.yml','docker-compose.dev.yml']:
        assert 'context: .\n      dockerfile: apps/web/Dockerfile' in (ROOT/name).read_text()
    assert './apps/web:/app:delegated' in (ROOT/'docker-compose.dev.yml').read_text()


def test_root_docker_context_is_default_deny_with_web_secret_exclusions():
    ignore=(ROOT/'apps/web/Dockerfile.dockerignore').read_text().splitlines()
    assert '**' in ignore and '!apps/web/**' in ignore
    for name in ['apps/web/node_modules','apps/web/.next','apps/web/.env*','apps/web/.git','apps/web/.vercel']:
        assert name in ignore
    assert '!apps/api/**' not in ignore and '!secrets/**' not in ignore
