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
    start=time.perf_counter()
    model=SentenceTransformer(str(path),device='cpu',local_files_only=True,trust_remote_code=False)
    model.max_seq_length=256
    load_ms=(time.perf_counter()-start)*1000
    # Same document fields as current importer, excluding synthetic metadata.
    products=catalog['products']
    texts=[]
    for row in products:
        attrs=' '.join(f'{k}: {v}' for k,v in row['attributes'].items() if not k.startswith(('_','fixture_')) and k!='image_kind')
        texts.append(f"{row['name']} {attrs} {row['description']} {row['category']} {row['currency']} {' '.join(row['tags'])}")
    started=time.perf_counter()
    docs=model.encode(texts,prompt=a.document_prompt,normalize_embeddings=True,batch_size=1,show_progress_bar=False)
    corpus_ms=(time.perf_counter()-started)*1000
    rankings={}
    for q in dataset['queries']:
        if q['split']!=a.split:continue
        started=time.perf_counter()
        vector=model.encode(q['query'],prompt=a.query_prompt,normalize_embeddings=True,show_progress_bar=False)
        scores=docs@vector
        # Deterministic stable tie ordering; no unsupported score threshold.
        indices=np.argsort(-scores,kind='stable')[:50]
        rankings[q['id']]={'skus':[products[int(i)]['sku'] for i in indices],'latency_ms':(time.perf_counter()-started)*1000}
    print(json.dumps({'catalog_sha256':sha,'rankings':rankings,'metadata':{'mode':'local_exact_dense_reference','model_path':str(path),'query_prompt':a.query_prompt,'document_prompt':a.document_prompt,'threads':a.threads,'max_seq_length':256,'dimension':int(docs.shape[1]),'startup_ms':load_ms,'corpus_encode_ms':corpus_ms,'corpus_vectors_persisted':False,'downloads':False,'production_index_measured':False,'no_match_policy':'Always top50, no threshold: false positives characterize lack of abstention, not semantic accuracy.'}},ensure_ascii=False))
if __name__=='__main__':main()
