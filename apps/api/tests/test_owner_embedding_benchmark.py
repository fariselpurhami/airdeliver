"""Manifest, offline command and real CLI validation; no model or network executed."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_pinned_official_candidates_only_and_exact_download_bound():
    rows=load('owner_embedding_benchmark').definitions()
    assert set(rows)=={'granite','harrier'}
    assert rows['harrier']['repo']=='microsoft/harrier-oss-v1-0.6b'
    assert rows['granite']['repo']=='ibm-granite/granite-embedding-311m-multilingual-r2'
    assert sum(r['download_bytes'] for r in rows.values())==1865940766
    assert all(any(f['path'].endswith('.safetensors') and len(f['sha256'])==64 for f in r['files']) for r in rows.values())


def test_local_artifact_integrity_rejects_missing_or_mismatched_bytes(tmp_path):
    runner=load('owner_embedding_benchmark')
    data={'files':[{'path':'config.json','size':2,'sha256':None}]}
    with pytest.raises(FileNotFoundError):runner.validate_files(tmp_path,data)
    (tmp_path/'config.json').write_text('{}')
    runner.validate_files(tmp_path,data)
    (tmp_path/'config.json').write_text('bad')
    with pytest.raises(ValueError):runner.validate_files(tmp_path,data)


def test_no_baseline_download_command_and_no_unspecified_model():
    script=ROOT/'scripts/owner_embedding_benchmark.py'
    for args in [('download','--model','baseline-current'),('run',)]:
        result=subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True)
        assert result.returncode==2


def test_existing_runner_cannot_run_registry_id_or_implicitly_download(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/run_cached_fixture_retrieval.py'),'--model-path',str(tmp_path/'not-cached'),'--query-prompt',''],text=True,capture_output=True)
    assert result.returncode!=0 and 'FileNotFoundError' in result.stderr


@pytest.mark.parametrize('grade',[float('nan'),float('inf'),-1,3,True,'2'])
def test_scorer_rejects_invalid_grade_instead_of_dropping_it(tmp_path,grade):
    import hashlib
    catalog=tmp_path/'catalog.json';catalog.write_text('{"products":[{"sku":"a"}]}')
    sha=hashlib.sha256(catalog.read_bytes()).hexdigest()
    queries=tmp_path/'queries.json';queries.write_text(json.dumps({'catalog_sha256':sha,'queries':[{'id':'q','split':'dev','review_status':'human_reviewed','kind':'exact','qrels':{'a':grade},'no_match':False}]}))
    ranking=tmp_path/'ranking.json';ranking.write_text(json.dumps({'catalog_sha256':sha,'rankings':{'q':{'skus':['a']}}}))
    with pytest.raises(ValueError,match='qrel'):load('evaluate_fixture_retrieval').evaluate(catalog,queries,ranking)

@pytest.mark.asyncio
@pytest.mark.parametrize('architecture',['qwen2','qwen3','modernbert'])
async def test_real_tiny_local_architecture_through_cpu_runner_offline(tmp_path,architecture):
    """Random tiny local weights verify runtime, never model relevance."""
    import torch
    from transformers import AutoModel,PreTrainedTokenizerFast,Qwen2Config,Qwen3Config,ModernBertConfig
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from sentence_transformers import SentenceTransformer,models
    configs={
        'qwen2':Qwen2Config(vocab_size=8,hidden_size=16,intermediate_size=32,num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,max_position_embeddings=512,pad_token_id=0),
        'qwen3':Qwen3Config(vocab_size=8,hidden_size=16,intermediate_size=32,num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,head_dim=8,max_position_embeddings=512,pad_token_id=0),
        'modernbert':ModernBertConfig(vocab_size=8,hidden_size=16,intermediate_size=32,num_hidden_layers=1,num_attention_heads=2,max_position_embeddings=512,pad_token_id=0,cls_token_id=1,sep_token_id=2,bos_token_id=1,eos_token_id=2,local_attention=8,global_attn_every_n_layers=1),
    }
    path=tmp_path/'model';path.mkdir()
    torch.manual_seed(44)
    AutoModel.from_config(configs[architecture],attn_implementation='eager').save_pretrained(path,safe_serialization=True)
    from transformers import BertTokenizer
    (path/'vocab.txt').write_text('[PAD]\n[CLS]\n[SEP]\n[UNK]\nshirt\ncotton\nblack\nsize\n')
    BertTokenizer(vocab=str(path/'vocab.txt'),unk_token='[UNK]',pad_token='[PAD]',cls_token='[CLS]',sep_token='[SEP]',model_max_length=256).save_pretrained(path)
    transformer=models.Transformer(str(path),model_args={'attn_implementation':'eager'})
    SentenceTransformer(modules=[transformer,models.Pooling(16,pooling_mode='cls' if architecture=='modernbert' else 'lasttoken'),models.Normalize()]).save(str(path))
    result=subprocess.run([sys.executable,str(ROOT/'scripts/run_cached_fixture_retrieval.py'),'--model-path',str(path),'--query-prompt','','--run-local-model','--smoke'],cwd=ROOT,text=True,capture_output=True,env={**__import__('os').environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'},timeout=60)
    assert result.returncode==0,result.stderr
    run=json.loads(result.stdout)
    assert len(run['rankings'])==2 and run['metadata']['corpus_count']==2
    assert run['metadata']['dimension']==16 and run['metadata']['smoke'] is True


def test_actual_comparison_cli_rejects_incomplete_results_without_models(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/compare_fixture_benchmarks.py'),'--directory',str(tmp_path)],text=True,capture_output=True)
    assert result.returncode!=0 and 'FileNotFoundError' in result.stderr


def test_paired_file_comparison_does_not_promote_synthetic_winner(tmp_path):
    queries=json.loads((ROOT/'fixtures/retrieval_eval/queries_v1.json').read_text())
    rankings={q['id']:{'skus':list(q['qrels'])[:50]} for q in queries['queries'] if q['split']=='dev'}
    for label in ['baseline-current','baseline-instructed','harrier','granite']:
        (tmp_path/(label+'-dev.rankings.json')).write_text(json.dumps({'catalog_sha256':queries['catalog_sha256'],'rankings':rankings,'metadata':{'smoke':False,'corpus_count':1000,'dtype':'float32'}}))
    import sys
    sys.path.insert(0,str(ROOT/'scripts'))
    try:result=load('compare_fixture_benchmarks').compare(tmp_path)
    finally:sys.path.remove(str(ROOT/'scripts'))
    assert result['automatic_switch'] is False and result['acceptance_pass'] is False
    assert result['paired_against_current_query_policy']['granite']['paired_ndcg10_mean_delta']==0
