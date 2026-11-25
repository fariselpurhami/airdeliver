"""Pure offline scorer. Reads catalog/query/ranking files; never loads models/network."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


def evaluate(catalog_path, query_path, ranking_path, *, split='dev', allow_draft=False):
    raw=Path(catalog_path).read_bytes();catalog=json.loads(raw)
    dataset=json.loads(Path(query_path).read_text());run=json.loads(Path(ranking_path).read_text())
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=dataset['catalog_sha256'] or digest!=run['catalog_sha256']:
        raise ValueError('Catalog SHA mismatch')
    products={p['sku']:p for p in catalog['products']}
    skus=set(products)
    queries=[q for q in dataset['queries'] if q['split']==split]
    if not queries or len({q['id'] for q in queries})!=len(queries):raise ValueError('Invalid query IDs/split')
    if not allow_draft and any(q['review_status']!='human_reviewed' for q in queries):
        raise ValueError('Draft labels require explicit --allow-draft; not an acceptance result')
    if set(run['rankings'])!={q['id'] for q in queries}:raise ValueError('Require every split query exactly once')
    metrics=[];no_match=[];latencies=[]
    for q in queries:
        row=run['rankings'][q['id']];ids=row['skus']
        if not isinstance(ids,list) or any(s not in skus for s in ids) or len(ids)!=len(set(ids)):raise ValueError('Unknown or duplicate ranked SKU')
        ms=row.get('latency_ms')
        if ms is not None:
            if type(ms) not in (float,int) or not math.isfinite(ms) or ms<0:raise ValueError('Invalid latency')
            latencies.append(ms)
        if not isinstance(q['qrels'],dict) or any(type(g) not in (int,float) or not math.isfinite(g) or g not in (0,1,2) for g in q['qrels'].values()):raise ValueError('Invalid qrel grades')
        if not set(q['qrels'])<=skus:raise ValueError('Unknown qrel')
        relevant={s:g for s,g in q['qrels'].items() if g>0}
        if not set(relevant)<=skus:raise ValueError('Unknown qrel')
        if q['no_match']:
            if relevant:raise ValueError('No-match qrels must be empty')
            no_match.append(bool(ids));continue
        if not relevant:raise ValueError('Relevant query has no labels')
        values={f'recall@{k}':len(set(ids[:k])&relevant.keys())/len(relevant) for k in (10,20,50)}
        dcg=sum((2**relevant.get(s,0)-1)/math.log2(i+2) for i,s in enumerate(ids[:10]))
        ideal=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(sorted(relevant.values(),reverse=True)[:10]))
        rule=q.get('label_basis',{})
        if q['kind']=='constraint' and rule.get('attribute'):
            def violates(sku):
                attrs=products[sku].get('attributes',{})
                return attrs.get('item_type')!=rule['item_type'] or ('equals' in rule and attrs.get(rule['attribute'])!=rule['equals']) or ('not_equals' in rule and attrs.get(rule['attribute'])==rule['not_equals'])
            values['hard_constraint_violation@10']=sum(violates(s) for s in ids[:10])/len(ids[:10]) if ids else 0.
        values['ndcg@10']=dcg/ideal
        values['mrr@10']=next((1/(i+1) for i,s in enumerate(ids[:10]) if s in relevant),0.)
        metrics.append((q,values))
    def mean(rows):return {k:statistics.mean(v[k] for _,v in rows) for k in ('recall@10','recall@20','recall@50','ndcg@10','mrr@10')} if rows else {}
    output={'catalog_sha256':digest,'split':split,'queries':len(queries),'draft_labels':any(q['review_status']!='human_reviewed' for q in queries),'acceptance_pass':False,'metrics':mean(metrics),'hard_constraint_violation@10':statistics.mean(v['hard_constraint_violation@10'] for _,v in metrics if 'hard_constraint_violation@10' in v) if any('hard_constraint_violation@10' in v for _,v in metrics) else None,'by_kind':{kind:mean([(q,v) for q,v in metrics if q['kind']==kind]) for kind in sorted({q['kind'] for q,_ in metrics})},'by_category':{category:mean([(q,v) for q,v in metrics if q.get('category')==category]) for category in sorted({q.get('category','unspecified') for q,_ in metrics})},'no_match_false_positive_rate':statistics.mean(no_match) if no_match else None,'latency_samples':len(latencies),'latency_p50_ms':statistics.median(latencies) if latencies else None,'latency_p95_ms':sorted(latencies)[max(0,math.ceil(.95*len(latencies))-1)] if latencies else None,'run_metadata':run.get('metadata',{}),'caveat':'Synthetic draft labels are not customer answer accuracy. No model/index/provider was executed by this scorer.'}
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',default='fixtures/dev_catalog_v1.json');p.add_argument('--queries',default='fixtures/retrieval_eval/queries_v1.json');p.add_argument('--rankings',required=True);p.add_argument('--split',choices=['dev','test'],default='dev');p.add_argument('--allow-draft',action='store_true')
    a=p.parse_args();print(json.dumps(evaluate(a.catalog,a.queries,a.rankings,split=a.split,allow_draft=a.allow_draft),indent=2))
if __name__=='__main__':main()
