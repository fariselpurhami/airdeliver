"""Offline benchmark evidence summaries, never a load generator."""
import importlib.util
from pathlib import Path
import pytest


def module():
 path=Path(__file__).parents[1]/'scripts/catalog_scale_evidence.py'
 spec=importlib.util.spec_from_file_location('scale_evidence',path)
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def evidence():
 return {'revision':'a'*40,'dataset_sha256':'b'*64,'synthetic':True,
 'model':{'name':'example','revision':'c'*40,'dimension':1536},
 'counts':{'postgres':1000000,'opensearch':1000000,'milvus':1000000},
 'scope':'retrieval_only','concurrency':1,'warmup_requests':10,
 'requests':[{'status':'success','latency_ms':100.0},{'status':'error','latency_ms':2000.0},{'status':'success','latency_ms':300.0}]}


def test_summary_includes_failure_latency_and_denominator():
 result=module().summarize(evidence())
 assert result['requests']==3 and result['errors']==1
 assert result['p95_ms']==2000 and result['max_ms']==2000
 assert result['reported_counts_equal_million'] is True
 assert result['one_second_observed_all_requests'] is False
 assert result['production_accepted'] is False

@pytest.mark.parametrize('mutation', ['mismatch','missing_latency','nan','bool_latency','negative','unknown_status','empty','bad_hash','fake_synthetic','bool_count'])
def test_incomplete_or_malformed_evidence_rejected(mutation):
 data=evidence()
 if mutation=='mismatch':data['counts']['milvus']=999999
 elif mutation=='missing_latency':del data['requests'][1]['latency_ms']
 elif mutation=='nan':data['requests'][0]['latency_ms']=float('nan')
 elif mutation=='bool_latency':data['requests'][0]['latency_ms']=True
 elif mutation=='negative':data['requests'][0]['latency_ms']=-1
 elif mutation=='unknown_status':data['requests'][0]['status']='timeout_hidden'
 elif mutation=='empty':data['requests']=[]
 elif mutation=='bad_hash':data['dataset_sha256']='placeholder'
 elif mutation=='fake_synthetic':data['synthetic']='true'
 elif mutation=='bool_count':data['counts']['postgres']=True
 with pytest.raises(ValueError):module().summarize(data)


def test_smaller_dataset_does_not_establish_million_or_concurrency_claim():
 data=evidence();data['counts']={k:1000 for k in data['counts']}
 result=module().summarize(data)
 assert result['reported_counts_equal_million'] is False
 assert result['concurrency']==1 and result['scope']=='retrieval_only'
