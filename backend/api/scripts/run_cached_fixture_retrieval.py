"""Owner-run local dense reference evaluation. No downloads, stores or providers.

Requires an explicit existing model directory and explicit --run-local-model.
Not production Milvus/OpenSearch or approximate-index measurement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import sys
import resource
import statistics


def validate_path(value):
    path=Path(value).expanduser().resolve(strict=True)
    if not path.is_dir() or not (path/'config.json').is_file():
        raise ValueError('Supply an existing local model directory, not a registry model ID')
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',default='fixtures/dev_catalog_v1.json')
    p.add_argument('--queries',default='fixtures/retrieval_eval/queries_v1.json')
    p.add_argument('--model-path',required=True);p.add_argument('--query-prompt',required=True,help='Exact reviewed query instruction, empty string only when model specifies none')
    p.add_argument('--vector-cache');p.add_argument('--pilot-docs',type=int);
    p.add_argument('--model-revision',default='unknown');p.add_argument('--smoke',action='store_true');
    p.add_argument('--document-prompt',default='');p.add_argument('--split',choices=['dev','test'],default='dev')
    p.add_argument('--run-local-model',action='store_true');p.add_argument('--threads',type=int,default=2)
    a=p.parse_args();path=validate_path(a.model_path)
    if not a.run_local_model:raise SystemExit('No model executed. Owner must explicitly pass --run-local-model after approval.')
    if not 1<=a.threads<=4:raise ValueError('Threads must be1..4')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    import torch
    import numpy as np
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(a.threads)
    raw=Path(a.catalog).read_bytes();catalog=json.loads(raw);dataset=json.loads(Path(a.queries).read_text())
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=dataset['catalog_sha256']:raise ValueError('Catalog SHA mismatch')
    if a.smoke and a.pilot_docs:raise ValueError('Smoke and pilot are separate modes')
    if a.pilot_docs and not 20<=a.pilot_docs<=50:raise ValueError('Pilot requires20..50 documents')
    start=time.perf_counter()
    print('Loading local model, offline, CPU float32',file=sys.stderr,flush=True)
    model=SentenceTransformer(str(path),device='cpu',local_files_only=True,trust_remote_code=False,model_kwargs={'dtype':torch.float32,'attn_implementation':'eager'})
    model.max_seq_length=256
    load_ms=(time.perf_counter()-start)*1000
    # Standardized document fields with synthetic metadata excluded.
    # Not an exact replay of current importer/index document serialization.
    products=catalog['products'][:2] if a.smoke else catalog['products']
    texts=[]
    for row in products:
        attrs=' '.join(f'{k}: {v}' for k,v in row['attributes'].items() if not k.startswith(('_','fixture_')) and k!='image_kind')
        texts.append(f"{row['name']} {attrs} {row['description']} {row['category']} {row['currency']} {' '.join(row['tags'])}")
    if a.pilot_docs:
        from fixture_vector_cache import pilot_indices
        indices=pilot_indices(products,a.pilot_docs)
        durations=[]
        for n,i in enumerate(indices):
            started=time.perf_counter()
            result=model.encode([texts[i]],prompt=a.document_prompt,normalize_embeddings=True,batch_size=1,show_progress_bar=False,convert_to_numpy=True)
            if not np.isfinite(result).all():raise ValueError('Invalid pilot vector')
            durations.append(time.perf_counter()-started)
            print('Pilot document '+str(n+1)+'/'+str(len(indices))+' seconds='+str(round(durations[-1],3)),file=sys.stderr,flush=True)
        steady=durations[1:]
        ordered=sorted(steady)
        print(json.dumps({'catalog_sha256':sha,'pilot':True,'rankings':{},'metadata':{'model_revision':a.model_revision,'startup_ms':load_ms,'document_count':len(indices),'sample_skus':[products[i]['sku'] for i in indices],'category_counts':{cat:sum(products[i]['category']==cat for i in indices) for cat in sorted({products[i]['category'] for i in indices})},'document_seconds':durations,'steady_median_seconds':statistics.median(steady),'steady_p95_seconds':ordered[max(0,__import__('math').ceil(.95*len(ordered))-1)],'projected1000docs_hours_at_mean':statistics.mean(steady)*1000/3600,'projection_is_upper_bound':False,'queries_measured':False,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),'batch_size':1,'threads':a.threads,'dtype':'float32','max_seq_length':256,'vectors_persisted':False,'caveat':'Category-spread pilot, not full quality benchmark or guaranteed runtime. Excludes queries and future throttling/paging.'}}))
        return
    contract=None;cached=None
    if a.vector_cache and not a.smoke:
        from fixture_vector_cache import binding,read
        print('Hashing local model/corpus to verify vector reuse binding',file=sys.stderr,flush=True)
        contract=binding(path,a.model_revision,sha,products,texts,a.document_prompt,a.threads)
        cached=read(a.vector_cache,contract)
        if cached:
            from fixture_vector_cache import validate
            validate(cached[0],len(products),model.get_sentence_embedding_dimension())
    started=time.perf_counter()
    docs=cached[0] if cached else model.encode(texts,prompt=a.document_prompt,normalize_embeddings=True,batch_size=1,show_progress_bar=True,convert_to_numpy=True)
    if not np.isfinite(docs).all() or np.any(np.linalg.norm(docs,axis=1)==0):raise ValueError('Invalid document vectors')
    corpus_ms=(time.perf_counter()-started)*1000
    if contract and not cached:
        from fixture_vector_cache import write
        write(a.vector_cache,contract,docs,corpus_ms)
    if cached:print('Verified document vectors reused; document encoding skipped',file=sys.stderr,flush=True)
    rankings={}
    selected=[q for q in dataset['queries'] if q['split']==a.split]
    if a.smoke:selected=selected[:2]
    print('Encoding queries: '+str(len(selected)),file=sys.stderr,flush=True)
    for q in selected:
        if q['split']!=a.split:continue
        started=time.perf_counter()
        vector=model.encode(q['query'],prompt=a.query_prompt,normalize_embeddings=True,show_progress_bar=False)
        if not np.isfinite(vector).all() or np.linalg.norm(vector)==0:raise ValueError('Invalid query vector')
        scores=docs@vector
        # Deterministic stable tie ordering; no unsupported score threshold.
        indices=np.argsort(-scores,kind='stable')[:50]
        rankings[q['id']]={'skus':[products[int(i)]['sku'] for i in indices],'latency_ms':(time.perf_counter()-started)*1000}
    print(json.dumps({'catalog_sha256':sha,'rankings':rankings,'metadata':{'mode':'local_exact_dense_reference','model_path':str(path),'query_prompt':a.query_prompt,'document_prompt':a.document_prompt,'threads':a.threads,'model_revision':a.model_revision,'dtype':'float32','attention':'eager','smoke':a.smoke,'corpus_count':len(products),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),'document_policy':'fixture fields with synthetic metadata excluded; not exact current-store document serialization','max_seq_length':256,'dimension':int(docs.shape[1]),'startup_ms':load_ms,'corpus_encode_ms':corpus_ms,'corpus_vectors_persisted':bool(contract),'document_vectors_reused':bool(cached),'original_corpus_encode_ms':cached[1]['original_corpus_encode_ms'] if cached else corpus_ms,'batch_size':1,'downloads':False,'production_index_measured':False,'no_match_policy':'Always top50, no threshold: false positives characterize lack of abstention, not semantic accuracy.'}},ensure_ascii=False))
if __name__=='__main__':main()
