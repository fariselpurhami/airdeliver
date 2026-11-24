"""Owner-only pinned local benchmark preparation. Never mutates application stores.

Download contacts Hugging Face for static files only. Run is strictly offline.
No remote Python code, provider inference, model deletion or index writes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'fixtures/retrieval_eval/models_v1.json'
BASE_REPO='Alibaba-NLP/gte-Qwen2-1.5B-instruct'
BASE_REVISION='a9af15a6372d7d6b25e9fb07c2ccb9e1fe645644'
INSTRUCTION='Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: '


def definitions():
    data=json.loads(MANIFEST.read_text())
    for row in data.values():
        if len(row['revision'])!=40 or any(c not in '0123456789abcdef' for c in row['revision']):raise ValueError('Unpinned revision')
        if row['license'] not in {'mit','apache-2.0'}:raise ValueError('Unreviewed licence')
        for f in row['files']:
            if Path(f['path']).is_absolute() or '..' in Path(f['path']).parts or f['path'].endswith(('.py','.bin','.pkl')):raise ValueError('Unsafe model file')
        if sum(f['size'] for f in row['files'])!=row['download_bytes']:raise ValueError('Manifest size mismatch')
    return data


def resolve(label):
    from huggingface_hub import snapshot_download
    if label.startswith('baseline'):
        roots=[os.environ.get('SENTENCE_TRANSFORMERS_HOME'),os.environ.get('HF_HUB_CACHE'),os.environ.get('TRANSFORMERS_CACHE'),None]
        for root in dict.fromkeys(roots):
            try:
                path=Path(snapshot_download(BASE_REPO,revision=BASE_REVISION,cache_dir=root,local_files_only=True,token=False))
                if (path/'config.json').is_file() and list(path.glob('*.safetensors')):return path,BASE_REVISION
            except FileNotFoundError:pass
            except Exception as exc:
                if type(exc).__name__!='LocalEntryNotFoundError':raise
        raise FileNotFoundError('Pinned baseline absent from known local caches; no baseline downloaded')
    d=definitions()[label]
    return Path(snapshot_download(d['repo'],revision=d['revision'],cache_dir=os.environ.get('HF_HUB_CACHE'),local_files_only=True,token=False)),d['revision']


def validate_files(path,row):
    for f in row['files']:
        p=path/f['path']
        if p.stat().st_size!=f['size']:raise ValueError('Model file size mismatch: '+f['path'])
        if f['sha256']:
            h=hashlib.sha256()
            with p.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
            if h.hexdigest()!=f['sha256']:raise ValueError('Model file SHA mismatch: '+f['path'])


def download(label):
    # Explicit download action only. Local run subprocess restores offline mode.
    os.environ['HF_HUB_OFFLINE']='0'
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from huggingface_hub import hf_hub_download
    d=definitions()[label]
    cache=Path(os.environ.get('HF_HUB_CACHE') or os.environ.get('HF_HOME',Path.home()/'.cache/huggingface'));cache.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(cache).free<d['download_bytes']*2+2*1024**3:raise ValueError('Need twice selected download plus2GiB free space')
    for f in d['files']:
        print('Downloading or verifying cached file: '+f['path']+' ('+str(f['size'])+' bytes)',flush=True)
        hf_hub_download(d['repo'],f['path'],revision=d['revision'],cache_dir=os.environ.get('HF_HUB_CACHE'),token=False)
    path,_=resolve(label);validate_files(path,d)
    print(json.dumps({'downloaded':label,'revision':d['revision'],'selected_bytes':d['download_bytes'],'licence':d['license'],'hosted_inference':False,'application_stores_changed':False}))


def run(label,output,split,smoke,pilot_docs=None):
    path,revision=resolve(label)
    if label.startswith('baseline'):
        limits=[Path(p).read_text().strip() for p in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory/memory.limit_in_bytes') if Path(p).is_file()]
        finite=[int(x) for x in limits if x.isdigit() and int(x)<2**60]
        if finite and min(finite)<8*1024**3:raise ValueError('Baseline requires the existing8GiB tools container, not6GiB API limit')
        if Path('/proc/meminfo').is_file():
            available=next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
            if available<8*1024**3:raise ValueError('Baseline requires8GiB available host memory; pause other model services first, no limit was raised')
    if label in definitions():validate_files(path,definitions()[label])
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    suffix='pilot'+str(pilot_docs) if pilot_docs else 'smoke' if smoke else split
    dest=output/(label+'-'+suffix+'.rankings.json')
    if dest.exists():raise ValueError('Refusing to overwrite an existing run: '+str(dest))
    prompt='' if label=='baseline-current' else INSTRUCTION if label=='baseline-instructed' else definitions()[label]['query_prompt']
    command=[sys.executable,str(ROOT/'scripts/run_cached_fixture_retrieval.py'),'--model-path',str(path),'--query-prompt',prompt,'--split',split,'--run-local-model','--model-revision',revision]
    if smoke:command+=['--smoke']
    elif pilot_docs:command+=['--pilot-docs',str(pilot_docs)]
    else:command+=['--vector-cache',str(output/'document-vectors-v1')]
    env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
    tmp=dest.with_suffix('.partial')
    started=time.time()
    try:
        with tmp.open('x') as stream:subprocess.run(command,cwd=ROOT,env=env,stdout=stream,check=True)
        result=json.loads(tmp.read_text());result['metadata']['profile']=label
        result['metadata']['production_index_measured']=False
        result['metadata']['baseline_semantics']='baseline-current means current unprompted query policy on the standardized fixture corpus, not a measurement of the active index'
        result['metadata']['wall_seconds']=round(time.time()-started,3)
        tmp.write_text(json.dumps(result,ensure_ascii=False));tmp.rename(dest)
    except BaseException:
        print('Run failed; partial artifact retained at '+str(tmp),file=sys.stderr);raise
    print(str(dest))
    if pilot_docs:print(json.dumps(result))
    if not smoke and not pilot_docs:
        from evaluate_fixture_retrieval import evaluate
        score=evaluate(ROOT/'fixtures/dev_catalog_v1.json',ROOT/'fixtures/retrieval_eval/queries_v1.json',dest,split=split,allow_draft=True)
        score_path=output/(label+'-'+split+'.scores.json');score_path.write_text(json.dumps(score,indent=2));print(json.dumps(score))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preflight','download','smoke','pilot','run'])
    p.add_argument('--pilot-docs',type=int,default=20,choices=range(20,51));p.add_argument('--model',choices=['baseline-current','baseline-instructed','harrier','granite']);p.add_argument('--output',default='/data/storage/embedding-benchmark-v1');p.add_argument('--split',choices=['dev','test'],default='dev')
    a=p.parse_args();definitions()
    if a.action=='preflight':
        import platform
        path,_=resolve('baseline-current')
        limits={}
        for file in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory/memory.limit_in_bytes'):
            if Path(file).is_file():limits[file]=Path(file).read_text().strip()
        print(json.dumps({'architecture':platform.machine(),'ram_gib':round(os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')/2**30,2),'baseline_cached':str(path),'cgroup_memory_limits':limits,'free_disk_bytes':shutil.disk_usage(path).free,'candidate_download_bytes':{k:v['download_bytes'] for k,v in definitions().items()},'downloads':False,'provider_calls':False}));return
    if not a.model:p.error('--model required')
    if a.action=='download':
        if a.model.startswith('baseline'):p.error('Baseline must already be cached')
        download(a.model)
    else:run(a.model,a.output,a.split,a.action=='smoke',a.pilot_docs if a.action=='pilot' else None)
if __name__=='__main__':main()
