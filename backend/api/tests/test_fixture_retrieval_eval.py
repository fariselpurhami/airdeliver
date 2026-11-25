import hashlib
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
scorer=module('evaluate_fixture_retrieval')

def test_dataset_is_140_draft_balanced_queries_bound_to_exact_fixture_sha():
    data=json.loads((ROOT/'fixtures/retrieval_eval/queries_v1.json').read_text())
    assert data['catalog_sha256']==hashlib.sha256((ROOT/'fixtures/dev_catalog_v1.json').read_bytes()).hexdigest()
    assert len(data['queries'])==140 and len({q['id'] for q in data['queries']})==140
    assert sum(q['split']=='dev' for q in data['queries'])==70
    assert all(q['review_status']=='draft_requires_human_review' for q in data['queries'])
    for cat in {q['category'] for q in data['queries']}:
        rows=[q for q in data['queries'] if q['category']==cat]
        assert len(rows)==20 and sum(q['no_match'] for q in rows)==2


def inputs(tmp_path,ids,*,draft=False):
    catalog={'products':[{'sku':s} for s in ('a','b','c')]};raw=json.dumps(catalog).encode();sha=hashlib.sha256(raw).hexdigest()
    files=[tmp_path/n for n in ('catalog.json','queries.json','run.json')]
    files[0].write_bytes(raw)
    files[1].write_text(json.dumps({'catalog_sha256':sha,'queries':[{'id':'q','split':'dev','kind':'exact','review_status':'draft' if draft else 'human_reviewed','qrels':{'a':2,'b':1},'no_match':False}]}))
    files[2].write_text(json.dumps({'catalog_sha256':sha,'rankings':{'q':{'skus':ids,'latency_ms':3}}}))
    return files


def test_metrics_from_known_rankings_no_model_or_network(tmp_path):
    result=scorer.evaluate(*inputs(tmp_path,['c','a','b']))
    assert result['metrics']['recall@10']==1 and result['metrics']['mrr@10']==.5
    assert 0<result['metrics']['ndcg@10']<1 and result['latency_p95_ms']==3
    assert result['acceptance_pass'] is False

@pytest.mark.parametrize('ids',[['unknown'],['a','a']])
def test_malformed_predictions_reject(tmp_path,ids):
    with pytest.raises(ValueError):scorer.evaluate(*inputs(tmp_path,ids))

def test_draft_labels_never_silently_become_acceptance(tmp_path):
    files=inputs(tmp_path,['a'],draft=True)
    with pytest.raises(ValueError,match='Draft'):scorer.evaluate(*files)
    assert scorer.evaluate(*files,allow_draft=True)['draft_labels'] is True

def test_model_id_cannot_trigger_download(tmp_path):
    runner=module('run_cached_fixture_retrieval')
    with pytest.raises(FileNotFoundError):runner.validate_path(str(tmp_path/'registry-model-name'))
