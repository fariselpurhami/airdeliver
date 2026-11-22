"""Exercise the dev backup script against CI's disposable Docker database."""
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import psycopg
from psycopg import sql
import pytest
from sqlalchemy.engine import make_url

pytestmark=pytest.mark.skipif(os.environ.get('TEST_DOCKER_ENGINE')!='1',reason='Docker engine integration is enabled on CI')
ROOT=Path(__file__).resolve().parents[3]


def test_backup_script_and_real_restore_keep_existing_product(tmp_path):
    url=make_url(os.environ['TEST_POSTGRES_DSN'])
    assert (url.database or '').startswith('airdeliver_test_')
    container=os.environ['AIRDELIVER_POSTGRES_CONTAINER']
    assert container and not container.startswith('-')
    connection=dict(host=url.host,port=url.port or 5432,user=url.username,password=url.password)
    restore='airdeliver_test_restore_'+uuid.uuid4().hex[:12]
    sku='backup-sentinel-'+uuid.uuid4().hex
    product_id=None
    restore_created=False
    try:
        with psycopg.connect(**connection,dbname=url.database) as db:
            product_id=db.execute("""INSERT INTO products
                (sku,name,description,price,currency,inventory,category,tags,attributes,is_active,created_at,updated_at)
                VALUES (%s,'Backup sentinel','Do not replace',1.25,'USD',3,'test','[]','{}',true,now(),now()) RETURNING id""",(sku,)).fetchone()[0]
        (tmp_path/'scripts').mkdir()
        shutil.copyfile(ROOT/'scripts/backup_dev_db.sh',tmp_path/'scripts/backup_dev_db.sh')
        result=subprocess.run(['bash',str(tmp_path/'scripts/backup_dev_db.sh')],capture_output=True,text=True)
        assert result.returncode==0, result.stderr
        archive=next(p for p in (tmp_path/'backups').iterdir() if not p.name.endswith(('.txt','.list')))
        assert archive.read_bytes()[:5]==b'PGDMP'
        assert Path(str(archive)+'.preflight.txt').exists()
        with psycopg.connect(**connection,dbname='postgres',autocommit=True) as db:
            db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restore)))
            restore_created=True
        with archive.open('rb') as source:
            restored=subprocess.run(['docker','exec','-i',container,'pg_restore','--username',url.username,'--dbname',restore,'--no-owner','--exit-on-error'],stdin=source,capture_output=True)
        assert restored.returncode==0, restored.stderr.decode(errors='replace')
        query='SELECT id,sku,name,price,inventory,created_at,updated_at FROM products WHERE id=%s'
        with psycopg.connect(**connection,dbname=url.database) as original, psycopg.connect(**connection,dbname=restore) as copied:
            assert original.execute(query,(product_id,)).fetchone()==copied.execute(query,(product_id,)).fetchone()
        if os.environ.get('TEST_PG_BACKUP_IMAGE'):
            verify_production_backup_image(tmp_path,url,container,product_id)
    finally:
        if product_id is not None:
            with psycopg.connect(**connection,dbname=url.database) as db:
                db.execute('DELETE FROM products WHERE id=%s AND sku=%s',(product_id,sku))
        if restore_created:
            # Only this test's newly created, random disposable database.
            with psycopg.connect(**connection,dbname='postgres',autocommit=True) as db:
                db.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(restore)))


def verify_production_backup_image(tmp_path, url, container, product_id):
    import json
    image=os.environ['TEST_PG_BACKUP_IMAGE']
    details=json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
    network=next(iter(details['NetworkSettings']['Networks']))
    folder=tmp_path/'production-backups'; folder.mkdir()
    env=dict(os.environ,POSTGRES_HOST='postgres',POSTGRES_PORT='5432',POSTGRES_USER=url.username,
             POSTGRES_PASSWORD=url.password,POSTGRES_DB=url.database)
    args=['docker','run','--rm','--network',network,'--user',f'{os.getuid()}:{os.getgid()}','-v',str(folder)+':/backups']
    for key in ('POSTGRES_HOST','POSTGRES_PORT','POSTGRES_USER','POSTGRES_PASSWORD','POSTGRES_DB'):
        args+=['--env',key]
    result=subprocess.run([*args,image,'/backup.sh'],capture_output=True,text=True,env=env)
    assert result.returncode==0,result.stderr
    archive=next((folder/'last').glob('*.dump'))
    assert archive.read_bytes()[:5]==b'PGDMP'
    target='airdeliver_test_image_restore_'+uuid.uuid4().hex[:10]
    connection=dict(host=url.host,port=url.port or 5432,user=url.username,password=url.password)
    try:
        restored=subprocess.run([*args,image,'/restore.sh','/backups/last/'+archive.name,target],capture_output=True,text=True,env=env)
        assert restored.returncode==0,restored.stderr
        query='SELECT id,sku,name,price,inventory,created_at,updated_at FROM products WHERE id=%s'
        with psycopg.connect(**connection,dbname=url.database) as original, psycopg.connect(**connection,dbname=target) as copied:
            assert original.execute(query,(product_id,)).fetchone()==copied.execute(query,(product_id,)).fetchone()
        # A second restore to an existing target must refuse before touching it.
        refused=subprocess.run([*args,image,'/restore.sh','/backups/last/'+archive.name,target],capture_output=True,text=True,env=env)
        assert refused.returncode!=0
        with psycopg.connect(**connection,dbname=target) as copied:
            assert copied.execute('SELECT count(*) FROM products WHERE id=%s',(product_id,)).fetchone()[0]==1
    finally:
        with psycopg.connect(**connection,dbname='postgres',autocommit=True) as db:
            db.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(target)))
