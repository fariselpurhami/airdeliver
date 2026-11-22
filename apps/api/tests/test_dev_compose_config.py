"""Local Compose config contracts, no daemon, app containers or real secrets."""
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = runpy.run_path(str(ROOT / 'scripts/configure_dev_env.py'))
OVERRIDE = os.environ.get('TEST_DOCKER_COMPOSE_BIN')
COMPOSE = [OVERRIDE] if OVERRIDE else ['docker', 'compose']
pytestmark = pytest.mark.skipif(not OVERRIDE and not shutil.which('docker'), reason='Docker Compose config CLI required, no daemon needed')


def config(root, files, env_file, *, success=True):
    args = [*COMPOSE, '--project-directory', str(root), '--env-file', str(env_file), '-p', 'airdeliver_dev']
    for name in files:
        args += ['-f', str(ROOT / name)]
    env = dict(os.environ, LOCAL_UID=str(os.getuid()), LOCAL_GID=str(os.getgid()))
    result = subprocess.run([*args, 'config', '--format', 'json'], capture_output=True, text=True, env=env)
    if not success:
        assert result.returncode != 0
        return None
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture
def prepared(tmp_path):
    shutil.copyfile(ROOT / '.env.dev.example', tmp_path / '.env.dev.example')
    # Mounted files override stale .env credentials, just as the app does.
    (tmp_path / '.env').write_text('POSTGRES_USER=stale\nPOSTGRES_PASSWORD=stale\nPOSTGRES_DB=stale\nRABBITMQ_USER=stale\nRABBITMQ_PASS=stale\nRABBITMQ_COOKIE=existing-dev-cookie\n')
    originals = {'postgres_user':'existing-user', 'postgres_password':"original @:$x/\\'password", 'postgres_db':'existing-db', 'rabbitmq_user':'existing-broker', 'rabbitmq_pass':'existing-broker-pass'}
    (tmp_path / 'secrets').mkdir()
    for name,value in originals.items():
        (tmp_path / 'secrets' / name).write_text(value + '\n')
    source = config(tmp_path, ['docker-compose.dev-setup.yml'], Path('/dev/null'))['services']['configure']['environment']
    # Compose escapes literal dollars in serialized config for safe reloading.
    source = {key: value.replace('$$', '$') if isinstance(value,str) else value for key,value in source.items()}
    if os.environ.get('TEST_DOCKER_ENGINE') == '1':
        (tmp_path/'scripts').mkdir()
        shutil.copyfile(ROOT/'scripts/configure_dev_env.py', tmp_path/'scripts/configure_dev_env.py')
        args=[*COMPOSE,'--project-directory',str(tmp_path),'--env-file','/dev/null','-p','airdeliver_dev','-f',str(ROOT/'docker-compose.dev-setup.yml'),'run','--rm','-T','configure']
        env=dict(os.environ,LOCAL_UID=str(os.getuid()),LOCAL_GID=str(os.getgid()))
        result=subprocess.run(args,capture_output=True,text=True,env=env)
        assert result.returncode==0, result.stderr
    else:
        MODULE['prepare'](tmp_path, True, source)
    return tmp_path, originals


def test_combined_dev_preserves_volume_credentials_and_disables_unconfigured_payments(prepared, monkeypatch):
    root, originals = prepared
    model = config(root, ['docker-compose.yml', 'docker-compose.dev.yml'], root / '.env.dev')
    services = model['services']
    assert services['postgres']['image'].startswith('pgvector/pgvector:0.8.7-pg19-bookworm@sha256:')
    mounts = services['postgres']['volumes']
    assert any(v.get('source')=='postgres19-data' and v['target']=='/var/lib/postgresql' for v in mounts)
    assert not any(v.get('source')=='postgres-data' for v in mounts)
    assert model['volumes']['postgres19-data']['name'] == 'airdeliver_dev_postgres19-data'
    for name in ('api','api-worker','api-migrator'):
        values = services[name]['environment']
        assert values['APP_ENV']=='development'
        assert values['LEGACY_TIMESTAMP_TIMEZONE']==''
        assert values['DATABASE_URI'].startswith('postgresql+asyncpg://')
    values = services['api']['environment']
    assert values['STRIPE_SECRET_KEY']=='' and values['STRIPE_PUBLISHABLE_KEY']==''
    from app.core.config import CoreSettings
    # Load the effective container environment, mapping mounted paths to their
    # actual local fixture files. BaseSettings performs its real JSON decoding.
    for key,value in values.items():
        if key.endswith('_FILE') and value.startswith('/run/secrets/'):
            value = str(root/'secrets/dev'/Path(value).name)
        monkeypatch.setenv(key, value)
    settings = CoreSettings(_env_file=None)
    assert settings.POSTGRES_USER==originals['postgres_user']
    assert settings.POSTGRES_PASSWORD.get_secret_value()==originals['postgres_password']
    assert settings.POSTGRES_DB==originals['postgres_db']
    assert not settings.COOKIES_SECURE
    for name,value in originals.items():
        assert (root/'secrets'/name).read_text()==value+'\n'
        assert (root/'secrets/dev'/name).read_text()==value+'\n'
    assert 'stale' in (root/'.env').read_text()
    assert (root/'.env.dev').stat().st_mode & 0o777 == 0o600
    assert services['web']['environment']['NEXT_PUBLIC_API_URL'].endswith('/api/v1')
    assert '--experimental-https' not in ' '.join(services['web']['command'])
    assert services['web']['environment']['NEXTAUTH_URL']==services['web']['environment']['AUTH_URL']


def test_production_still_refuses_missing_core_values(tmp_path):
    config(tmp_path, ['docker-compose.yml'], Path('/dev/null'), success=False)


def test_existing_config_is_never_overwritten(prepared):
    root,_ = prepared
    before = (root/'.env.dev').read_bytes()
    with pytest.raises(ValueError, match='already exists'):
        MODULE['prepare'](root, True, {})
    assert (root/'.env.dev').read_bytes()==before


def test_existing_credentials_are_not_guessed(tmp_path):
    shutil.copyfile(ROOT/'.env.dev.example', tmp_path/'.env.dev.example')
    with pytest.raises(ValueError, match='will not be guessed'):
        MODULE['prepare'](tmp_path, True, {})
    assert not (tmp_path/'.env.dev').exists()
    assert not (tmp_path/'secrets/dev').exists()


def test_env_serialization_roundtrips_special_characters(tmp_path):
    values = ["space # / @ : ${UNSET} $$", "a'b", 'end'+chr(92), 'a'+chr(92)+'b$literal']
    path=tmp_path/'.env'
    for value in values:
        path.write_text('SAMPLE='+MODULE['env_value'](value)+'\n')
        probe=tmp_path/'probe.yml'
        probe.write_text(json.dumps({'services':{'probe':{'image':'busybox:1.37','env_file':str(path)}}}))
        result=subprocess.run([*COMPOSE,'--project-directory',str(tmp_path),'--env-file',str(path),'-f',str(probe),'config','--format','json'],capture_output=True,text=True)
        assert result.returncode==0
        got=json.loads(result.stdout)['services']['probe']['environment']['SAMPLE'].replace('$$','$')
        assert got==value
