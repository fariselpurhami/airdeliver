"""Actual imported profile/loader/index contracts, no model download/calls."""
import json,os,subprocess,sys
from pathlib import Path
import pytest
from app.core.catalog_contract import SPACES,retrieval_space

def test_spaces_are_distinct_and_unknown_is_not_fallback():
    a,b=SPACES['gte-v1'],SPACES['harrier-v1']
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
from tools.seed_ultra_scale import Settings
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
    from tools.seed_ultra_scale import Settings
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
    monkeypatch.setattr(module,'PRODUCT_TEXT_PROFILE','harrier-v1')
    monkeypatch.setattr(module,'PRODUCT_TEXT_MODEL',SimpleNamespace(dimension=2))
    value=await engine._get_query_embedding('  blue shirt  ')
    assert value==[1.,0.]
    assert calls==[('blue shirt',{'convert_to_numpy':True,'prompt':SPACES['harrier-v1'].query_prompt,'normalize_embeddings':True})]

@pytest.mark.asyncio
async def test_owner_migration_actual_control_flow_readonly_sha_memory_and_counts(monkeypatch,capsys):
    from scripts import migrate_harrier_catalog as migration
    from app.db import session as session_module
    from app.core import config
    from tools import seed_ultra_scale as seed
    import pymilvus
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import numpy as np
    rows=[SimpleNamespace(**{f:None for f in migration.FIELDS})]
    rows[0].id=8;rows[0].sku='old-stable-sku';rows[0].attributes={}
    sql=[]
    class Session:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def execute(self,statement):
            sql.append(str(statement));return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:rows))
        async def rollback(self):sql.append('ROLLBACK')
    monkeypatch.setattr(session_module,'AsyncSessionFactory',Session)
    monkeypatch.setattr(config,'get_core_settings',lambda:SimpleNamespace(DATABASE_URI='postgresql+asyncpg://unused/test',APP_ENV='development'))
    memory=[{'id':17,'user_id':2,'fact_text':'likes blue','timestamp':11}]
    state={'built':False,'memory':[],'operations':[],'iter_closed':False}
    class Iterator:
        first=True
        def next(self):
            if self.first:self.first=False;return memory
            return []
        def close(self):state['iter_closed']=True
    class Client:
        def __init__(self,**kwargs):pass
        def has_collection(self,name):return name==migration.SOURCE.memory_collection or state['built']
        def query_iterator(self,**kwargs):return Iterator()
        def get_collection_stats(self,name):return {'row_count':len(state['memory']) if name==migration.TARGET.memory_collection else 1}
        def create_schema(self,**kwargs):
            assert kwargs['auto_id'] is True
            return SimpleNamespace(add_field=lambda **kwargs:None)
        def prepare_index_params(self):return SimpleNamespace(add_index=lambda **kwargs:None)
        def create_collection(self,**kwargs):state['built']=True
        def insert(self,**kwargs):state['memory']+=kwargs['data']
        def flush(self,**kwargs):pass
        def close(self):pass
    monkeypatch.setattr(pymilvus,'MilvusClient',Client)
    def forbidden(*args,**kwargs):raise AssertionError('Dryrun loaded model or wrote index')
    monkeypatch.setattr(seed,'EmbeddingService',forbidden)
    args=SimpleNamespace(apply=False,reviewed_sha256=None,expected_products=1)
    await migration.run(args)
    dry=json.loads(capsys.readouterr().out);assert dry['products']==1 and dry['memory_records']==1
    assert state['iter_closed'] and not state['built'] and sql[0]=='SET TRANSACTION READ ONLY'
    args.apply=True;args.reviewed_sha256='bad'
    with pytest.raises(ValueError,match='SHA'):await migration.run(args)
    assert not state['built']
    class Repository:
        def __init__(self,*args):
            self._client=SimpleNamespace(indices=SimpleNamespace(refresh=AsyncMock()),count=AsyncMock(return_value={'count':1}))
        async def close(self):pass
    monkeypatch.setattr(seed,'MilvusRepository',Repository);monkeypatch.setattr(seed,'OpenSearchRepository',Repository)
    class Encoder:
        def encode(self,text,**kwargs):
            assert text=='likes blue' and kwargs['prompt']==migration.TARGET.query_prompt and kwargs['normalize_embeddings']
            return np.array([1.]+[0.]*1023)
    monkeypatch.setattr(seed,'EmbeddingService',lambda *args:SimpleNamespace(_model=Encoder()))
    from app.services import real_catalog_import
    async def sync(products,*args):
        assert products[0]['id']==8;state['operations'].append('candidate');return {'milvus':1,'opensearch':1}
    monkeypatch.setattr(real_catalog_import,'sync_import',sync)
    args.reviewed_sha256=dry['sha256'];await migration.run(args)
    migrated=state['memory'][0]
    assert migrated['source_memory_id']==17 and 'id' not in migrated
    assert {k:migrated[k] for k in ('user_id','fact_text','timestamp')}=={k:memory[0][k] for k in ('user_id','fact_text','timestamp')}
    assert state['operations']==['candidate']
    # Existing target facts cannot be silently duplicated by rerun.
    with pytest.raises(ValueError,match='Nonempty'):await migration.run(args)

def test_granite_fresh_process_contract_is_pinned_separate_and_empty_prompt():
    env={**os.environ,'PRODUCT_TEXT_PROFILE':'granite-v1','PRODUCT_TEXT_MODEL_REVISION':''}
    for key in ('EMBEDDING_MODEL','SEED_EMBEDDING_DIMENSION','SEED_EMBEDDING_REVISION','MILVUS_COLLECTION','OPENSEARCH_INDEX'):env.pop(key,None)
    code='''
import json
from app.core.catalog_contract import *
from app.core.ai_profile import get_ai_profile
from app.services.ai_commerce_engine import AICommerceEngine
from tools.seed_ultra_scale import Settings
p=get_ai_profile();s=Settings(_env_file=None,DATABASE_URI='postgresql+asyncpg://unused/test',APP_ENV='development')
print(json.dumps([p.text_retrieval_model,p.text_retrieval_revision,p.text_retrieval_dimension,s.embedding_dimension,s.embedding_model,PRODUCT_QUERY_PROMPT,PRODUCT_SEARCH_INDEX,{k:v.name for k,v in AICommerceEngine.SCHEMA_CONFIG.items()}]))
'''
    result=subprocess.run([sys.executable,'-c',code],env=env,text=True,capture_output=True,check=True)
    x=json.loads(result.stdout.splitlines()[-1]);g=SPACES['granite-v1']
    assert x[:7]==[g.model,g.revision,768,768,g.model,'',g.search_index]
    assert x[7]['product_text']==g.collection and x[7]['memory']==g.memory_collection and x[7]['intent']==g.intent_collection
    for field in ('collection','search_index','intent_collection','memory_collection'):
        assert len({getattr(v,field) for v in SPACES.values()})==3
