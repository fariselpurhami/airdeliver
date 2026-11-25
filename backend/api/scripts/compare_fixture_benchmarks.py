"""Paired descriptive synthetic-fixture comparison, never automatic promotion."""
import argparse
import json
from pathlib import Path
import random
import statistics
from evaluate_fixture_retrieval import evaluate

ROOT=Path(__file__).resolve().parents[1]

def compare(directory,split='dev'):
    directory=Path(directory)
    labels=['baseline-current','baseline-instructed','harrier','granite']
    scores={};runs={}
    dataset=json.loads((ROOT/'fixtures/retrieval_eval/queries_v1.json').read_text())
    queries=[q for q in dataset['queries'] if q['split']==split and not q['no_match']]
    def ndcg(q,row):
        import math
        grades=q['qrels'];ideal=sum((2**v-1)/math.log2(i+2) for i,v in enumerate(sorted(grades.values(),reverse=True)[:10]))
        return sum((2**grades.get(s,0)-1)/math.log2(i+2) for i,s in enumerate(row['skus'][:10]))/ideal
    for label in labels:
        file=directory/(label+'-'+split+'.rankings.json')
        scores[label]=evaluate(ROOT/'fixtures/dev_catalog_v1.json',ROOT/'fixtures/retrieval_eval/queries_v1.json',file,split=split,allow_draft=True)
        runs[label]=json.loads(file.read_text())
        metadata=runs[label]['metadata']
        if metadata.get('smoke') or metadata.get('corpus_count')!=1000 or metadata.get('dtype')!='float32':raise ValueError('Need complete standardized float32 runs')
    comparisons={}
    for label in labels[1:]:
        deltas=[ndcg(q,runs[label]['rankings'][q['id']])-ndcg(q,runs['baseline-current']['rankings'][q['id']]) for q in queries]
        rng=random.Random(7721)
        samples=sorted(statistics.mean(rng.choices(deltas,k=len(deltas))) for _ in range(2000))
        comparisons[label]={'paired_ndcg10_mean_delta':statistics.mean(deltas),'descriptive_bootstrap_95pct':[samples[49],samples[1949]],'queries':len(deltas)}
    return {'split':split,'draft_labels':True,'acceptance_pass':False,'automatic_switch':False,'scores':scores,'paired_against_current_query_policy':comparisons,'caveat':'Synthetic assistant-authored labels, related query templates and no human adjudication. Bootstrap interval is descriptive, not independent customer-quality confidence. No active Milvus/BM25/index measured. Review Arabic/category/constraint/no-match and resources before any decision. Baseline instructed control can explain query-instruction gains without changing models.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',default='/data/storage/embedding-benchmark-v1');p.add_argument('--split',choices=['dev','test'],default='dev');a=p.parse_args();print(json.dumps(compare(a.directory,a.split),indent=2))
