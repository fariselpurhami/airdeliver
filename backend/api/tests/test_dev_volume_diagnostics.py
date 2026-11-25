import json
from pathlib import Path
import runpy
import sys
import pytest
ROOT=Path(__file__).resolve().parents[3]
QUIET=runpy.run_path(str(ROOT/'scripts/dev_compose_quiet_volumes.py'))
INSPECT=runpy.run_path(str(ROOT/'scripts/inspect_dev_volumes.py'))


def warning(name='airdeliver_dev_redis-data'):
    return f'volume "{name}" carries the compose label "redis-data" but does not match the compose file (using "new"); it is left untouched - remove it manually if it is no longer needed'


def test_filter_matches_only_project_stale_label_warning():
    predicate=QUIET['is_stale_volume_warning']
    assert predicate(warning())
    assert predicate('time="date" level=warning msg="'+warning().replace('"','\\"')+'"')
    for line in ['ERROR: volume in use', 'WARN: disk full',warning('other_project_data'),
                 'Volume exists but recreate? data will be lost',warning()+' ERROR disk full']:
        assert not predicate(line)


def test_wrapper_preserves_other_warnings_stdout_and_exit_status(tmp_path,capfd):
    fake=tmp_path/'compose.py'
    fake.write_text('import sys,json\nprint(json.dumps(sys.argv[1:]))\nprint('+repr(warning())+',file=sys.stderr)\nprint("WARN unrelated",file=sys.stderr)\nsys.exit(7)\n')
    assert QUIET['run'](['ps'],executable=[sys.executable,str(fake)])==7
    out,err=capfd.readouterr()
    assert 'WARN unrelated' in err and 'left untouched' not in err
    args=json.loads(out)
    assert args==['--env-file','.env.dev','-f','docker-compose.yml','-f','docker-compose.dev.yml','-p','airdeliver_dev','ps']
    assert QUIET['run'](['--show-stale-volume-warnings','ps'],executable=[sys.executable,str(fake)])==7
    assert 'left untouched' in capfd.readouterr().err


def test_inventory_reads_all_containers_and_never_prints_resolved_secrets(monkeypatch,capsys):
    calls=[]
    def read(args):
        calls.append(args)
        if args[-3:]==['config','--format','json']:
            return json.dumps({'services':{'redis':{'environment':{'SECRET':'PRIVATE_SECRET'},'volumes':[{'type':'volume','source':'redis-data','target':'/data'}]}},'volumes':{'redis-data':{'name':'current_volume'}}})
        if args[:3]==['docker','volume','ls']:return 'airdeliver_dev_old\n'
        if args==['docker','ps','-aq']:return 'stopped-id\n'
        if args==['docker','inspect','stopped-id']:
            return json.dumps([{'Name':'/stopped-db','State':{'Status':'exited'},'Mounts':[{'Type':'volume','Name':'airdeliver_dev_old'}]}])
        if args[:3]==['docker','volume','inspect']:
            return json.dumps([{'Name':'airdeliver_dev_old','Driver':'local','Labels':{}}])
        if args==['docker','system','df','-v']:return 'Local Volumes: 13MB'
        pytest.fail('unexpected command '+repr(args))
    INSPECT['inspect'].__globals__['read']=read
    INSPECT['inspect']()
    out=capsys.readouterr().out
    assert 'current_volume' in out and 'stopped-db [exited]' in out and '13MB' in out
    assert 'PRIVATE_SECRET' not in out
    assert all(not any(word in args for word in ['rm','prune','up','down','run','exec']) for args in calls)
