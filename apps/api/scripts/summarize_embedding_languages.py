"""Rescore existing local rankings by query script and identifier-only group. Never runs a model."""
import argparse,json,tempfile
from pathlib import Path
try:from .evaluate_fixture_retrieval import evaluate
except ImportError:from evaluate_fixture_retrieval import evaluate
ROOT=Path(__file__).resolve().parents[1]

def summarize(directory):
    query_path=ROOT/'fixtures/retrieval_eval/queries_v1.json'
    dataset=json.loads(query_path.read_text());out={}
    for model in ('granite','harrier'):
        ranking=Path(directory)/(model+'-dev.rankings.json')
        # Full original validation before making language subsets.
        evaluate(ROOT/'fixtures/dev_catalog_v1.json',query_path,ranking,split='dev',allow_draft=True)
        run=json.loads(ranking.read_text());out[model]={}
        import re
        def group(q):
            if re.search(r'[\u0600-\u06ff]',q['query']):return 'arabic_script'
            if q['query'].startswith('ADL-DEV-v1-'):return 'sku_identifier_only'
            return 'english_text'
        languages=sorted({group(q) for q in dataset['queries'] if q['split']=='dev'})
        for language in languages:
            selected=[q for q in dataset['queries'] if q['split']=='dev' and group(q)==language]
            ids={q['id'] for q in selected}
            with tempfile.TemporaryDirectory() as folder:
                qp=Path(folder)/'queries.json';rp=Path(folder)/'ranking.json'
                qp.write_text(json.dumps({**dataset,'queries':selected}))
                rp.write_text(json.dumps({**run,'rankings':{k:v for k,v in run['rankings'].items() if k in ids}}))
                score=evaluate(ROOT/'fixtures/dev_catalog_v1.json',qp,rp,split='dev',allow_draft=True)
            out[model][language]={k:score[k] for k in ('queries','metrics','by_kind','latency_p50_ms','latency_p95_ms')}
    return {'models':out,'grouping':'Arabic-script queries separate; SKU-only excluded from English text. Other fixture queries manually English-authored. No language labels existed in dataset.', 'caveat':'Synthetic DRAFT dev labels only. Not active-index/customer accuracy. English and Arabic not interchangeable. No inference, download or writes to application stores.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',default='/data/storage/embedding-benchmark-v1')
    print(json.dumps(summarize(p.parse_args().directory),indent=2))
