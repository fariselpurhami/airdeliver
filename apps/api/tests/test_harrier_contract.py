"""Actual imported profile/loader/index contracts, no model download/calls."""
import json,os,subprocess,sys
from pathlib import Path
import pytest
from app.core.catalog_contract import SPACES,retrieval_space

def test_spaces_are_distinct_and_unknown_is_not_fallback():
    a,b=SPACES.values()
    for field in ('collection','search_index','intent_collection','memory_collection'):
        assert getattr(a,field)!=getattr(b,field)
    assert (b.dimension,len(b.revision))==(1024,40)
    assert b.query_prompt.endswith('\nQuery: ')
    with pytest.raises(ValueError):retrieval_space('typo')

def test_harrier_selection_reaches_real_consumers_in_fresh_process():
    code='''
import json
from app.core.catalog_contract import *
from app.core.ai_profile import get_ai_profile
from app.services.ai_commerce_engine import AICommerceEngine,PRODUCT_TEXT_MODEL,PRODUCT_SEARCH_INDEX,PRODUCT_QUERY_PROMPT
from seed_ultra_scale import Settings
p=get_ai_profile();s=Settings(_env_file=None,DATABASE_URI='postgresql+asyncpg://unused/test',APP_ENV='development')
print(json.dumps({'model':p.text_retrieval_model,'dim':PRODUCT_TEXT_MODEL.dimension,'revision':p.text_retrieval_revision,'collections':{k:v.name for k,v in AICommerceEngine.SCHEMA_CONFIG.items()},'os':PRODUCT_SEARCH_INDEX,'seed':s.embedding_model,'seed_dim':s.embedding_dimension,'seed_revision':s.embedding_revision,'prompt':PRODUCT_QUERY_PROMPT}))
'''
    env={**os.environ,'PRODUCT_TEXT_PROFILE':'harrier-v1','PRODUCT_TEXT_MODEL_REVISION':''}
    for key in ('EMBEDDING_MODEL','SEED_EMBEDDING_DIMENSION','SEED_EMBEDDING_REVISION','MILVUS_COLLECTION','OPENSEARCH_INDEX'):env.pop(key,None)
    result=subprocess.run([sys.executable,'-c',code],env=env,text=True,capture_output=True,check=True)
    data=json.loads(result.stdout.splitlines()[-1]);h=SPACES['harrier-v1']
    assert data['model']==data['seed']==h.model
    assert data['dim']==data['seed_dim']==1024
    assert data['revision']==data['seed_revision']==h.revision
    assert data['collections']=={'product_text':h.collection,'product_visual':'airdeliver_visual_sota_v4','intent':h.intent_collection,'memory':h.memory_collection}
    assert data['os']==h.search_index and data['prompt']==h.query_prompt

def test_known_candidate_namespace_rejects_wrong_model_even_if_os_only():
    from seed_ultra_scale import Settings
    with pytest.raises(ValueError,match='versioned index'):
        Settings(_env_file=None,DATABASE_URI='postgresql+asyncpg://unused/test',APP_ENV='development',MILVUS_ENABLED=False,
            OPENSEARCH_INDEX=SPACES['harrier-v1'].search_index)

def test_migration_digest_covers_contents_ids_memory_and_contract():
    from scripts.migrate_harrier_catalog import digest
    a=[{'id':1,'name':'same'}];m=[{'id':5,'fact_text':'fact','timestamp':1}]
    assert digest(a,m)==digest(a,m)
    assert digest(a,m)!=digest([{'id':2,'name':'same'}],m)
    assert digest(a,m)!=digest(a,[{**m[0],'timestamp':2}])

def test_existing_rankings_language_summary_is_offline_and_separates_sku(tmp_path):
    from scripts import summarize_embedding_languages as summary
    catalog=json.loads((summary.ROOT/'fixtures/dev_catalog_v1.json').read_text())
    queries=json.loads((summary.ROOT/'fixtures/retrieval_eval/queries_v1.json').read_text())
    rankings={'catalog_sha256':queries['catalog_sha256'],'rankings':{q['id']:{'skus':list(q['qrels'])[:50],'latency_ms':1} for q in queries['queries'] if q['split']=='dev'}}
    for model in ('granite','harrier'):(tmp_path/(model+'-dev.rankings.json')).write_text(json.dumps(rankings))
    data=summary.summarize(tmp_path)['models']
    assert data['granite']==data['harrier']
    assert set(data['granite'])=={'english_text','arabic_script','sku_identifier_only'}
    assert sum(v['queries'] for v in data['granite'].values())==70

@pytest.mark.asyncio
async def test_real_query_boundary_sends_official_prompt_and_normalization(monkeypatch):
    from app.services import ai_commerce_engine as module
    from types import SimpleNamespace
    import numpy as np
    calls=[]
    class Encoder:
        def encode(self,value,**kwargs):
            calls.append((value,kwargs));return np.array([1.,0.])
    engine=object.__new__(module.AICommerceEngine)
    encoder=Encoder();engine.embedding_model=encoder;engine.limits=SimpleNamespace(max_query_length=100,embedding_timeout_seconds=2)
    monkeypatch.setattr(module,'PRODUCT_QUERY_PROMPT',SPACES['harrier-v1'].query_prompt)
    monkeypatch.setattr(module,'PRODUCT_TEXT_MODEL',SimpleNamespace(dimension=2))
    value=await engine._get_query_embedding('  blue shirt  ')
    assert value==[1.,0.]
    assert calls==[('blue shirt',{'convert_to_numpy':True,'prompt':SPACES['harrier-v1'].query_prompt,'normalize_embeddings':True})]
