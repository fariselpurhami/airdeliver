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


def test_fresh_cli_generates_private_credentials_and_isolates_unknown_volumes(tmp_path):
    import sys
    shutil.copyfile(ROOT/'.env.dev.example',tmp_path/'.env.dev.example')
    (tmp_path/'scripts').mkdir()
    shutil.copyfile(ROOT/'scripts/configure_dev_env.py',tmp_path/'scripts/configure_dev_env.py')
    source=config(tmp_path,['docker-compose.dev-setup.yml'],Path('/dev/null'))['services']['configure']['environment']
    source={key:value.replace('$$','$') if isinstance(value,str) else str(value) for key,value in source.items()}
    if os.environ.get('TEST_DOCKER_ENGINE')=='1':
        args=[*COMPOSE,'--project-directory',str(tmp_path),'--env-file','/dev/null','-p','airdeliver_dev','-f',str(ROOT/'docker-compose.dev-setup.yml'),'run','--rm','-T','configure','--fresh']
        env=dict(os.environ,LOCAL_UID=str(os.getuid()),LOCAL_GID=str(os.getgid()))
    else:
        args=[sys.executable,str(tmp_path/'scripts/configure_dev_env.py'),'--fresh']
        env={**os.environ,**source}
    result=subprocess.run(args,capture_output=True,text=True,env=env)
    assert result.returncode==0,result.stderr
    model=config(tmp_path,['docker-compose.yml','docker-compose.dev.yml'],tmp_path/'.env.dev')
    db_volume=model['volumes']['postgres19-data']['name']
    mq_volume=model['volumes']['rabbitmq-data']['name']
    assert db_volume.startswith('airdeliver_dev_postgres19_fresh_')
    assert mq_volume.startswith('airdeliver_dev_rabbitmq_fresh_')
    assert db_volume!='airdeliver_dev_postgres-data' and mq_volume!='airdeliver_dev_rabbitmq-data'
    for name in ('redis-data','opensearch-data'):
        assert model['volumes'][name]['name']==db_volume+'_'+name
    for name in ('etcd-data','milvus-data'):
        assert model['volumes'][name]['name']==db_volume+'_rustfs_v1_'+name
    assert model['volumes']['rustfs-data']['name']==db_volume+'_rustfs_v1_data'
    for field in ('postgres_password','rabbitmq_pass'):
        path=tmp_path/'secrets/dev'/field
        assert len(path.read_text().strip())>=32
        assert path.stat().st_mode&0o777==0o600
        assert path.read_text().strip() not in result.stdout
    assert not (tmp_path/'.env').exists()
    assert (tmp_path/'.env.dev').stat().st_mode&0o777==0o600
    before=(tmp_path/'.env.dev').read_bytes()
    repeated=subprocess.run(args,capture_output=True,text=True,env=env)
    assert repeated.returncode!=0 and 'already exists' in repeated.stderr
    assert (tmp_path/'.env.dev').read_bytes()==before



def test_seeder_compose_uses_real_settings_aliases_and_independent_network(prepared,monkeypatch):
    root,_=prepared
    monkeypatch.setenv('COMPOSE_PROFILES','tools')
    model=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')
    service=model['services']['api-seeder']; values=service['environment']
    assert values['SEED_BATCH_SIZE']=='16' and values['EMBEDDING_ENCODE_BATCH_SIZE']=='1'
    assert 'network_mode' not in service and 'global-net' in service['networks']
    assert 'api' not in service['depends_on']
    from seed_ultra_scale import Settings
    parsed=Settings(_env_file=None,**values)
    assert parsed.target_count==1000 and parsed.batch_size==16
    assert parsed.embedding_model=='Alibaba-NLP/gte-Qwen2-1.5B-instruct'
    assert parsed.opensearch_user=='admin' and parsed.opensearch_pass


def test_dev_rustfs_is_free_local_and_cannot_inherit_aws_config(prepared, monkeypatch):
    root,_=prepared
    monkeypatch.setenv('S3_ENDPOINT','s3.eu-west-1.amazonaws.com:443')
    monkeypatch.setenv('S3_BUCKET_NAME','must-not-contact')
    monkeypatch.setenv('S3_USE_IAM','true')
    model=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')
    server=model['services']['minio']; milvus=model['services']['milvus']
    assert server['image'].startswith('rustfs/rustfs:1.0.6@sha256:')
    assert 'build' not in server and not server.get('profiles') and not server.get('ports')
    assert server['environment']['RUSTFS_ACCESS_KEY']==milvus['environment']['MINIO_ACCESS_KEY_ID']
    assert server['environment']['RUSTFS_SECRET_KEY']==milvus['environment']['MINIO_SECRET_ACCESS_KEY']
    assert not milvus.get('entrypoint')
    assert milvus['environment']['MINIO_ADDRESS']=='minio:9000'
    assert milvus['environment']['MINIO_BUCKETNAME']=='airdeliver-dev'
    assert milvus['environment']['MINIO_USESSL']=='false'
    assert milvus['environment']['MINIO_USEIAM']=='false'
    assert milvus['environment']['MINIO_USEVIRTUALHOST']=='false'
    assert model['volumes']['etcd-data']['name'].endswith('_rustfs_v1_etcd-data')
    assert model['volumes']['milvus-data']['name'].endswith('_rustfs_v1_milvus-data')
    # Compose prunes unreferenced definitions, but no Docker volume is removed.
    assert '  minio-data:' in (ROOT/'docker-compose.dev.yml').read_text()
    assert server['volumes'][0]['source']=='rustfs-data'


def test_production_has_external_s3_and_no_legacy_dependency(prepared):
    root,_=prepared
    model=config(root,['docker-compose.yml'],root/'.env.dev')
    assert 'minio' not in model['services'] # profile disabled by default
    milvus=model['services']['milvus']; env=milvus['environment']
    assert set(milvus['depends_on'])=={'etcd'}
    assert env['MINIO_USESSL']=='true' and env['MINIO_USEIAM']=='true'
    assert env['MINIO_USEVIRTUALHOST']=='true' and env['MINIO_CLOUDPROVIDER']=='aws'
    assert env['MINIO_ACCESS_KEY_ID']==env['MINIO_SECRET_ACCESS_KEY']==''
    assert 'S3_BUCKET_NAME must name a pre-created bucket' in milvus['entrypoint'][2]


def test_production_guard_rejects_incomplete_or_non_aws_settings(prepared):
    root,_=prepared
    guard=config(root,['docker-compose.yml'],root/'.env.dev')['services']['milvus']['entrypoint'][2].replace('$$','$')
    valid=dict(MINIO_BUCKETNAME='example-bucket',MINIO_REGION='us-east-1',MINIO_ADDRESS='s3.us-east-1.amazonaws.com:443',MINIO_USEIAM='true')
    # Replace only final exec with a sentinel, no network or Milvus binary needed.
    guard=guard.replace('exec milvus run standalone','exit 0')
    def run(overrides):
        return subprocess.run(['/bin/sh','-ec',guard],env={**valid,**overrides},capture_output=True).returncode
    assert run({})==0
    for override in ({'MINIO_BUCKETNAME':''},{'MINIO_REGION':''},{'MINIO_ADDRESS':'minio:9000'},{'MINIO_ADDRESS':'https://s3.us-east-1.amazonaws.com'},{'MINIO_USEIAM':'false'},{'MINIO_USEIAM':'bad'}):
        assert run(override)!=0
    assert run({'MINIO_USEIAM':'false','MINIO_ACCESS_KEY_ID':'dummy','MINIO_SECRET_ACCESS_KEY':'dummy'})==0


def test_proxy_upgrade_preserves_production_tls_and_does_not_force_docker_api(prepared):
    root,_=prepared
    prod=config(root,['docker-compose.yml'],root/'.env.dev')['services']['reverse-proxy']
    dev=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')['services']['reverse-proxy']
    assert prod['image']==dev['image']
    assert prod['image'].startswith('traefik:v3.7.19@sha256:')
    assert '--api.dashboard=false' in prod['command']
    assert '--entrypoints.web.http.redirections.entrypoint.scheme=https' in prod['command']
    assert '--providers.docker.exposedbydefault=false' in prod['command']
    assert '--api.insecure=true' not in prod['command']
    for proxy in (prod,dev):
        assert 'DOCKER_API_VERSION' not in proxy.get('environment',{})
        assert any(v['target']=='/var/run/docker.sock' and v.get('read_only') for v in proxy['volumes'])


def test_dev_routes_replace_all_production_tls_labels(prepared):
    root,_=prepared
    prod=config(root,['docker-compose.yml'],root/'.env.dev')['services']
    dev=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')['services']
    for name in ('api','web'):
        labels=dev[name]['labels']
        assert labels['traefik.http.routers.'+name+'.entrypoints']=='web'
        assert not any('.tls' in key or 'middlewares' in key for key in labels)
        assert 'localhost' in labels['traefik.http.routers.'+name+'.rule']
        assert prod[name]['labels']['traefik.http.routers.'+name+'.entrypoints']=='websecure'
        assert prod[name]['labels']['traefik.http.routers.'+name+'.tls.certresolver']=='letsencrypt'
    assert dev['grafana']['labels']=={'traefik.enable':'false'}
    assert prod['grafana']['labels']['traefik.http.routers.grafana.tls.certresolver']=='letsencrypt'


def test_worker_probe_matches_its_own_server_not_api_image(prepared):
    root,_=prepared
    for files in (['docker-compose.yml'],['docker-compose.yml','docker-compose.dev.yml']):
        services=config(root,files,root/'.env.dev')['services']
        worker=services['api-worker']['healthcheck']
        assert worker['test']==['CMD','curl','-f','--max-time','5','http://localhost:8081/health']
        assert 'http://localhost:8000/api/v1/health' in ' '.join(services['api']['healthcheck']['test'])
        assert worker['start_period']=='6m30s'
        assert services['api']['healthcheck']['start_period']=='6m30s'
    source=(ROOT/'apps/api/worker_entrypoint.py').read_text()
    assert 'HEALTH_SERVER_PORT: Final[int] = 8081' in source
    assert 'raise StartupDependencyError("No payment gateway is configured and available")' in source


def test_optional_hf_token_reaches_all_model_downloaders(prepared,monkeypatch):
    root,_=prepared
    monkeypatch.setenv('COMPOSE_PROFILES','tools')
    monkeypatch.setenv('HF_TOKEN','hf_not_a_real_credential_test_only')
    services=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')['services']
    for name in ('api','api-worker','api-seeder'):
        assert services[name]['environment']['HF_TOKEN']=='hf_not_a_real_credential_test_only'
        assert services[name]['environment']['HF_HOME']=='/data/storage/models_cache/huggingface'
        assert any(v['target']=='/data/storage' for v in services[name]['volumes'])


def test_seeder_cache_overrides_stale_env_file_and_stays_on_shared_mount(prepared, monkeypatch):
    root,_=prepared
    monkeypatch.setenv('COMPOSE_PROFILES','tools')
    with (root/'.env.dev').open('a') as env:
        env.write('\nSENTENCE_TRANSFORMERS_HOME=/datastorage/models/cache/sentence_transformers\nHF_HUB_CACHE=/root/ephemeral-hub\n')
    services=config(root,['docker-compose.yml','docker-compose.dev.yml'],root/'.env.dev')['services']
    for name in ('api','api-worker','api-seeder'):
        values=services[name]['environment']
        assert values['SENTENCE_TRANSFORMERS_HOME']=='/data/storage/models_cache/sentence_transformers'
        assert values['HF_HUB_CACHE']=='/data/storage/models_cache/huggingface/hub'
        assert any(v['type']=='bind' and v['target']=='/data/storage' for v in services[name]['volumes'])
