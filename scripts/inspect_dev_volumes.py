#!/usr/bin/env python3
"""Read-only Compose volume inventory. Does not print resolved environment."""
import json
import subprocess


def read(args):
    return subprocess.run(args,check=True,text=True,capture_output=True).stdout


def inspect():
    compose=['docker','compose','--env-file','.env.dev','-f','docker-compose.yml',
             '-f','docker-compose.dev.yml','-p','airdeliver_dev']
    model=json.loads(read(compose+['config','--format','json']))
    print('CURRENT COMPOSE VOLUME NAMES')
    for key,value in model.get('volumes',{}).items():
        print(key,'=>',value.get('name',key),'external=',value.get('external',False))
    print('\nCURRENT SERVICE VOLUME MOUNTS')
    for service,config in model.get('services',{}).items():
        for mount in config.get('volumes',[]):
            if mount.get('type')=='volume':
                print(service,mount.get('source'),'=>',mount.get('target'))
    volumes=set(read(['docker','volume','ls','-q','--filter','label=com.docker.compose.project=airdeliver_dev']).splitlines())
    volumes.update(read(['docker','volume','ls','-q','--filter','name=airdeliver_dev_']).splitlines())
    ids=read(['docker','ps','-aq']).splitlines()
    containers=json.loads(read(['docker','inspect',*ids])) if ids else []
    print('\nEXISTING VOLUMES AND ALL CONTAINER REFERENCES, INCLUDING STOPPED')
    for name in sorted(volumes):
        v=json.loads(read(['docker','volume','inspect',name]))[0]
        refs=[c.get('Name','').lstrip('/')+' ['+c.get('State',{}).get('Status','?')+']'
              for c in containers if any(m.get('Type')=='volume' and m.get('Name')==name
                                        for m in c.get('Mounts',[]))]
        print(json.dumps({'name':name,'driver':v.get('Driver'),'labels':v.get('Labels'),
                          'container_references':refs},ensure_ascii=False))
    print('\nDOCKER REPORTED PER-VOLUME SIZE/REFCOUNT TABLE')
    print(read(['docker','system','df','-v']))


if __name__=='__main__':inspect()
