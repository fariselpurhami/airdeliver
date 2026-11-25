#!/usr/bin/env python3
"""Disposable real Docker provider discovery + HTTP route, no app/user volumes."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen
import uuid

ROOT=Path(__file__).resolve().parents[2]

def main():
    # Read the exact production image from source, not a separately drifting tag.
    import re
    image=re.search(r'  reverse-proxy:\n    image: (\S+)',(ROOT/'docker-compose.yml').read_text()).group(1)
    identity=uuid.uuid4().hex[:12]
    project='adl-proxy-ci-'+identity
    print(subprocess.check_output(['docker','version','--format','{{json .Server}}'],text=True),flush=True)
    with tempfile.TemporaryDirectory(prefix='adl-proxy-ci-') as tmp:
        path=Path(tmp)/'compose.json'
        import os, runpy, shutil
        setup=runpy.run_path(str(ROOT/'scripts/dev/configure_dev_env.py'))
        shutil.copyfile(ROOT/'.env.dev.example',Path(tmp)/'.env.dev.example')
        base=['docker','compose','--project-directory',tmp,'--env-file','/dev/null','-f',str(ROOT/'docker-compose.dev-setup.yml')]
        source=json.loads(subprocess.check_output([*base,'config','--format','json'],text=True,env={**os.environ,'LOCAL_UID':str(os.getuid()),'LOCAL_GID':str(os.getgid())}))['services']['configure']['environment']
        source={k:v.replace('$$','$') if isinstance(v,str) else str(v) for k,v in source.items()}
        setup['prepare'](tmp,source_env=source,fresh=True)
        effective=json.loads(subprocess.check_output(['docker','compose','--project-directory',tmp,'--env-file',str(Path(tmp)/'.env.dev'),'-f',str(ROOT/'docker-compose.yml'),'-f',str(ROOT/'docker-compose.dev.yml'),'config','--format','json'],text=True))['services']
        services={'proxy':{'image':image,'command':effective['reverse-proxy']['command']+['--log.level=DEBUG'],
                     'volumes':['/var/run/docker.sock:/var/run/docker.sock:ro'],'ports':['127.0.0.1::80']}}
        for name in ('api','web','grafana'):
            labels=effective[name]['labels'].copy()
            port_key='traefik.http.services.'+name+'.loadbalancer.server.port'
            if port_key in labels:
                labels[port_key]='80' # probe HTTP backend only, real routing rules unchanged
            services[name]={'image':'traefik/whoami:v1.11.0','hostname':name,'labels':labels}
        path.write_text(json.dumps({'services':services}))
        compose=['docker','compose','--env-file','/dev/null','-p',project,'-f',str(path)]
        try:
            subprocess.run([*compose,'up','-d','--wait'],check=True)
            mapped=subprocess.check_output([*compose,'port','proxy','80'],text=True).strip()
            url='http://127.0.0.1:'+mapped.rsplit(':',1)[1]
            for route,expected in (('/', 'web'),('/api/v1/health','api')):
                error=None
                for _ in range(40):
                    try:
                        with urlopen(Request(url+route,headers={'Host':'localhost'}),timeout=2) as resp:
                            body=resp.read().decode();assert resp.status==200 and 'Hostname: '+expected in body
                        break
                    except Exception as exc:
                        error=type(exc).__name__;time.sleep(1)
                else:
                    raise RuntimeError('Combined-dev HTTP route unavailable '+route+': '+str(error))
            logs=subprocess.check_output([*compose,'logs','proxy'],text=True)
            assert 'Provider connection established with docker' in logs,logs
            assert 'client version 1.24 is too old' not in logs,logs
            assert 'Provider error, retrying' not in logs,logs
            assert "EntryPoint doesn't exist" not in logs,logs
            assert 'nonexistent certificate resolver' not in logs,logs
            print(json.dumps({'result':'passed','image':image,'docker_discovery':True,'real_http_route':True,'combined_dev_labels':True,'routes':['/','/api/v1/health'],'forced_api_version':False}),flush=True)
        finally:
            subprocess.run([*compose,'logs','--tail','45'],check=False)
            subprocess.run([*compose,'down','--remove-orphans'],check=True)

if __name__=='__main__':
    main()
