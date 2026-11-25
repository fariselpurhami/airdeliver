"""Execute only extracted shell against local inert stubs, never a database."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[3]

def command():
    source=(ROOT/'docker-compose.dev.yml').read_text()
    block=source.split('  api-migrator:',1)[1].split('\n  api:',1)[0]
    script=block.split('      - |\n',1)[1].split('    depends_on:',1)[0]
    return '\n'.join(line[8:] for line in script.splitlines()).replace('$$','$')

@pytest.mark.parametrize('value',[None,'0','false','true','yes','2',''])
def test_default_and_ambiguous_values_cannot_migrate_or_seed(tmp_path,value):
    env=dict(os.environ,PATH=str(tmp_path))
    env.pop('AIRDELIVER_DEV_ALLOW_MIGRATIONS',None)
    if value is not None:env['AIRDELIVER_DEV_ALLOW_MIGRATIONS']=value
    result=subprocess.run(['/bin/sh','-ec',command()],env=env,text=True,capture_output=True)
    assert result.returncode==0
    assert 'migration and seed skipped' in result.stdout
    assert not (tmp_path/'calls').exists()

def test_explicit_gate_retains_existing_sequence_and_stops_on_migration_failure(tmp_path):
    for name in ['alembic','python']:
        p=tmp_path/name
        p.write_text('#!/bin/sh\necho "'+name+' $*" >> "$CALLS"\nif [ "'+name+'" = alembic ]; then exit "${FAIL_MIGRATION:-0}"; fi\n')
        p.chmod(0o700)
    calls=tmp_path/'calls'
    env=dict(os.environ,PATH=str(tmp_path),CALLS=str(calls),AIRDELIVER_DEV_ALLOW_MIGRATIONS='1')
    result=subprocess.run(['/bin/sh','-ec',command()],env=env)
    assert result.returncode==0
    assert calls.read_text().splitlines()==['alembic upgrade head','python -m app.db.initial_data']
    calls.unlink();env['FAIL_MIGRATION']='23'
    result=subprocess.run(['/bin/sh','-ec',command()],env=env)
    assert result.returncode==23
    assert calls.read_text().splitlines()==['alembic upgrade head']

def test_gate_is_dev_only_and_requires_explicit_environment_forwarding():
    source=(ROOT/'docker-compose.dev.yml').read_text()
    assert 'AIRDELIVER_DEV_ALLOW_MIGRATIONS=${AIRDELIVER_DEV_ALLOW_MIGRATIONS:-0}' in source
    production=(ROOT/'docker-compose.yml').read_text()
    assert 'AIRDELIVER_DEV_ALLOW_MIGRATIONS' not in production
    assert 'alembic upgrade head &&' in production


def test_dev_migrator_reads_current_checkout_read_only_not_baked_revision_copy():
    source=(ROOT/'docker-compose.dev.yml').read_text()
    block=source.split('  api-migrator:',1)[1].split('\n  api:',1)[0]
    assert './backend/api:/app:ro' in block
    assert 'target: production' in block
    assert (ROOT/'backend/api/alembic/versions/0a7cd546f987_customer_memory_consent.py').is_file()
    assert 'WORKDIR /app' in (ROOT/'backend/api/Dockerfile').read_text()
