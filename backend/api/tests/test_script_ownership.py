"""Script aliases preserve CLI, import, root and copyable setup interfaces."""
from pathlib import Path
import os
import runpy
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[3]
SCRIPTS={
'configure_dev_env.py':'dev/configure_dev_env.py',
'dev_compose_quiet_volumes.py':'dev/dev_compose_quiet_volumes.py',
'inspect_dev_volumes.py':'dev/inspect_dev_volumes.py',
'catalog_synthesizer.py':'dev/catalog_synthesizer.py',
'download_personaplex.py':'dev/download_personaplex.py',
'backup_dev_db.sh':'ops/backup_dev_db.sh',
'safe_provider_trace.py':'ops/safe_provider_trace.py',
'python_lock_inventory.py':'ci/python_lock_inventory.py',
'verify_traefik_docker.py':'ci/verify_traefik_docker.py'}


def test_relative_legacy_aliases_resolve_without_duplicate_sources():
 for old,new in SCRIPTS.items():
  alias=ROOT/'scripts'/old
  assert alias.is_symlink() and not alias.readlink().is_absolute()
  assert alias.resolve()==(ROOT/'scripts'/new).resolve()


def test_root_resolution_and_read_only_import_interfaces():
 for name in ['scripts/verify_traefik_docker.py','scripts/ci/verify_traefik_docker.py']:
  assert runpy.run_path(str(ROOT/name))['ROOT']==ROOT
 for old,new in [('safe_provider_trace.py','ops/safe_provider_trace.py'),('python_lock_inventory.py','ci/python_lock_inventory.py')]:
  before=runpy.run_path(str(ROOT/'scripts'/old));after=runpy.run_path(str(ROOT/'scripts'/new))
  function='metadata' if old.startswith('safe') else 'inventory'
  assert function in before and function in after


@pytest.mark.parametrize('path',['scripts/configure_dev_env.py','scripts/dev/configure_dev_env.py','scripts/python_lock_inventory.py','scripts/ci/python_lock_inventory.py'])
def test_historical_and_canonical_help_remain_side_effect_free(path):
 result=subprocess.run([sys.executable,str(ROOT/path),'--help'],capture_output=True,text=True,check=True)
 assert 'usage:' in result.stdout


@pytest.mark.parametrize('canonical',[True,False])
def test_backup_both_paths_write_only_to_original_project_root(tmp_path,canonical):
 # Fake Docker, not a database. Verify root resolution and exact stdin forwarding.
 (tmp_path/'scripts/ops').mkdir(parents=True)
 source=ROOT/'scripts/ops/backup_dev_db.sh'
 target=tmp_path/'scripts/ops/backup_dev_db.sh';target.write_bytes(source.read_bytes())
 (tmp_path/'scripts/backup_dev_db.sh').symlink_to('ops/backup_dev_db.sh')
 bindir=tmp_path/'bin';bindir.mkdir();docker=bindir/'docker'
 docker.write_text('#!/bin/sh\ncase "$*" in *pg_dump*) printf PGDMPfixture;; *pg_restore*) cat >/dev/null; printf archive-list;; *psql*) cat >/dev/null; printf preflight;; esac\n')
 docker.chmod(0o755)
 script=target if canonical else tmp_path/'scripts/backup_dev_db.sh'
 result=subprocess.run(['bash',str(script)],cwd='/',env={**os.environ,'PATH':str(bindir)+':'+os.environ['PATH']},capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 assert len(list((tmp_path/'backups').glob('*.dump.*')))==3
 assert not (tmp_path/'scripts/backups').exists()
