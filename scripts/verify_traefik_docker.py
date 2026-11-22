#!/usr/bin/env python3
"""Disposable real Docker provider discovery + HTTP route, no app/user volumes."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen
import uuid

ROOT=Path(__file__).resolve().parents[1]

def main():
    # Read the exact production image from source, not a separately drifting tag.
    import re
    image=re.search(r'  reverse-proxy:\n    image: (\S+)',(ROOT/'docker-compose.yml').read_text()).group(1)
    identity=uuid.uuid4().hex[:12]
    project='adl-proxy-ci-'+identity
    print(subprocess.check_output(['docker','version','--format','{{json .Server}}'],text=True),flush=True)
    with tempfile.TemporaryDirectory(prefix='adl-proxy-ci-') as tmp:
        path=Path(tmp)/'compose.json'
        path.write_text(json.dumps({'services':{
            'proxy':{'image':image,'command':['--providers.docker=true','--providers.docker.exposedbydefault=false','--entrypoints.web.address=:80','--log.level=DEBUG'],
                     'volumes':['/var/run/docker.sock:/var/run/docker.sock:ro'],'ports':['127.0.0.1::80']},
            'echo':{'image':'traefik/whoami:v1.11.0','labels':{'traefik.enable':'true','traefik.http.routers.probe.rule':'Host(`proxy-test.local`)','traefik.http.routers.probe.entrypoints':'web','traefik.http.services.probe.loadbalancer.server.port':'80'}}}}))
        compose=['docker','compose','--env-file','/dev/null','-p',project,'-f',str(path)]
        try:
            subprocess.run([*compose,'up','-d','--wait'],check=True)
            mapped=subprocess.check_output([*compose,'port','proxy','80'],text=True).strip()
            url='http://127.0.0.1:'+mapped.rsplit(':',1)[1]
            error=None
            for _ in range(40):
                try:
                    with urlopen(Request(url,headers={'Host':'proxy-test.local'}),timeout=2) as resp:
                        body=resp.read().decode();assert resp.status==200 and 'Hostname:' in body
                    break
                except Exception as exc:
                    error=type(exc).__name__;time.sleep(1)
            else:
                raise RuntimeError('Docker-discovered HTTP route unavailable: '+str(error))
            logs=subprocess.check_output([*compose,'logs','proxy'],text=True)
            assert 'Provider connection established with docker' in logs,logs
            assert 'client version 1.24 is too old' not in logs,logs
            assert 'Provider error, retrying' not in logs,logs
            print(json.dumps({'result':'passed','image':image,'docker_discovery':True,'real_http_route':True,'forced_api_version':False}),flush=True)
        finally:
            subprocess.run([*compose,'logs','--tail','45'],check=False)
            subprocess.run([*compose,'down','--remove-orphans'],check=True)

if __name__=='__main__':
    main()
