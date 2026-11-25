"""Summarize supplied synthetic run evidence. No network, imports, model or load execution.

Input is a self-reported measurement artifact, not independent proof that a run
occurred. Counts and hashes need matching source receipts before acceptance.
"""
import argparse
import json
import math
from pathlib import Path
import re


def summarize(data):
    def require(condition,reason):
        if not condition:raise ValueError(reason)
    require(type(data) is dict,'object_required')
    for name,length in [('revision',40),('dataset_sha256',64)]:
        require(type(data.get(name)) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',data[name]) is not None,'invalid_'+name)
    require(data.get('synthetic') is True,'synthetic_only')
    model=data.get('model',{})
    require(type(model) is dict and type(model.get('name')) is str and bool(model['name']),'model_identity_required')
    require(type(model.get('revision')) is str and re.fullmatch('[0-9a-f]{40}',model['revision']) is not None,'model_revision_required')
    require(type(model.get('dimension')) is int and model['dimension']>0,'dimension_required')
    counts=data.get('counts',{})
    require(type(counts) is dict and set(counts)=={'postgres','opensearch','milvus'},'store_counts_required')
    require(all(type(v) is int and v>0 for v in counts.values()) and len(set(counts.values()))==1,'store_count_mismatch')
    require(data.get('scope') in {'retrieval_only','full_http_chat'},'invalid_scope')
    require(type(data.get('concurrency')) is int and data['concurrency']>0,'invalid_concurrency')
    require(type(data.get('warmup_requests')) is int and data['warmup_requests']>=0,'invalid_warmup')
    rows=data.get('requests')
    require(type(rows) is list and bool(rows),'requests_required')
    latencies=[];errors=0
    for row in rows:
        require(type(row) is dict and row.get('status') in {'success','error','timeout','cancelled'},'invalid_status')
        ms=row.get('latency_ms')
        require(type(ms) in {int,float} and math.isfinite(ms) and ms>=0,'invalid_latency')
        latencies.append(ms);errors+=row['status']!='success'
    latencies.sort()
    def percentile(q):return latencies[max(0,math.ceil(q*len(latencies))-1)]
    return {'revision':data['revision'],'dataset_sha256':data['dataset_sha256'],
        'model':model,'counts':counts,'scope':data['scope'],'concurrency':data['concurrency'],
        'warmup_requests':data['warmup_requests'],'requests':len(rows),'errors':errors,
        'error_rate':errors/len(rows),'p50_ms':percentile(.5),'p95_ms':percentile(.95),
        'p99_ms':percentile(.99),'max_ms':latencies[-1],
        'reported_counts_equal_million':all(v==1000000 for v in counts.values()),
        'one_second_observed_all_requests':errors==0 and latencies[-1]<=1000,
        'production_accepted':False,
        'caveat':'Self-reported counts/timings require original run receipts. Failed requests remain in every latency percentile. No correctness, capacity or production acceptance follows from this summary.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(json.loads(args.evidence.read_text())),indent=2,allow_nan=False))

if __name__=='__main__':main()
