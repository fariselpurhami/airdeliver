"""Real learned embeddings through PostgreSQL, Milvus and OpenSearch, CI only.

Uses a small 384-dimension model in isolated test indexes, never the API's
1536-dimension collection. This tests the complete path, not GTE model quality.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
import subprocess
import uuid

from huggingface_hub import snapshot_download
from sqlalchemy import text
from sqlalchemy.engine import make_url
import sys
API=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(API))
import seed_ultra_scale as seed


def main():
    dsn=os.environ.get('TEST_POSTGRES_DSN','')
    if os.environ.get('TEST_DOCKER_ENGINE')!='1' or not (make_url(dsn).database or '').startswith('airdeliver_test_'):
        raise SystemExit('Only TEST_DOCKER_ENGINE=1 and an airdeliver_test_* database are allowed')
    identity=uuid.uuid4().hex[:16]
    project='airdeliver-seed-ci-'+identity
    compose=['docker','compose','--env-file','/dev/null','-p',project,'-f',str(API.parents[1]/'docker-compose.seed-ci.yml')]
    backend=os.environ.get('TEST_OBJECT_STORAGE_BACKEND','rustfs')
    if backend not in {'rustfs','seaweed'}:
        raise SystemExit('Unknown disposable object storage backend')
    if backend!='minio':
        compose+=['-f',str(API.parents[1]/('docker-compose.storage-'+backend+'-ci.yml'))]
    try:
        subprocess.run([*compose,'up','-d','--build','--wait','--wait-timeout','240'],check=True)
        def port(service,number):
            output=subprocess.check_output([*compose,'port',service,str(number)],text=True).strip()
            return int(output.rsplit(':',1)[1])
        model=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41',token=False,
             allow_patterns=['*.json','model.safetensors','vocab.txt','*/config.json'])
        values=seed.Settings(_env_file=None,DATABASE_URI=dsn,APP_ENV='development',
            MILVUS_ENABLED=True,MILVUS_URI='http://127.0.0.1:'+str(port('milvus',19530)),MILVUS_COLLECTION='airdeliver_seed_e2e_'+identity,
            OPENSEARCH_ENABLED=True,OPENSEARCH_HOST='127.0.0.1',OPENSEARCH_PORT=port('opensearch',9200),
            OPENSEARCH_INDEX='airdeliver_seed_e2e_'+identity,OPENSEARCH_USE_SSL=False,OPENSEARCH_USER=None,OPENSEARCH_PASS=None,
            EMBEDDING_MODEL=model,SEED_EMBEDDING_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41',SEED_EMBEDDING_DIMENSION=384,SEED_TARGET_COUNT=17,SEED_BATCH_SIZE=7,
            SEED_RANDOM_SEED=int(identity,16),RETRY_ATTEMPTS=1)
        asyncio.run(verify(values,compose,backend))
    except BaseException:
        # Preserve exit/restart/OOM evidence before disposable cleanup. A gRPC
        # disconnect alone does not identify why a service disappeared.
        subprocess.run([*compose,'ps','--all'],check=False)
        containers=subprocess.run([*compose,'ps','--all','--quiet'],check=False,text=True,capture_output=True)
        if containers.stdout.strip():
            subprocess.run(['docker','inspect','--format',
                '{{.Name}} state={{json .State}} restarts={{.RestartCount}}',
                *containers.stdout.split()],check=False)
        subprocess.run([*compose,'logs','--tail','60'],check=False)
        raise
    finally:
        # Only this UUID project, with no persistent volumes or user data.
        subprocess.run([*compose,'down','--volumes','--remove-orphans'],check=True)


async def verify(settings,compose,backend):
    # Only this script's UUID-isolated disposable Milvus server. Prove the exact
    # empty legacy worker schema repairs through actual Milvus APIs, not mocks.
    from scripts.repair_empty_product_collection import repair
    from app.core.catalog_contract import PRODUCT_TEXT_COLLECTION, PRODUCT_TEXT_MODEL_DIMENSION
    def verify_empty_repair():
        client=seed.MilvusClient(uri=settings.milvus_uri)
        try:
            assert not client.has_collection(PRODUCT_TEXT_COLLECTION)
            schema=seed.MilvusClient.create_schema(auto_id=False,enable_dynamic_field=True)
            schema.add_field('id',seed.DataType.INT64,is_primary=True)
            schema.add_field('vector',seed.DataType.FLOAT_VECTOR,dim=PRODUCT_TEXT_MODEL_DIMENSION)
            schema.add_field('price',seed.DataType.FLOAT)
            schema.add_field('category',seed.DataType.VARCHAR,max_length=128)
            indexes=client.prepare_index_params()
            indexes.add_index(field_name='vector',metric_type='COSINE',index_type='HNSW',params={'M':16,'efConstruction':200})
            client.create_collection(collection_name=PRODUCT_TEXT_COLLECTION,schema=schema,index_params=indexes)
            result=repair(client,PRODUCT_TEXT_COLLECTION,apply=True,writers_stopped=True)
            assert result['missing_required_fields']==[] and result['writes_performed'] is True
        finally:client.close()
    await asyncio.to_thread(verify_empty_repair)
    async with seed.application_context(settings) as service:
        from app.services.embedding_warmup import warm_text_encoder
        warmup=await asyncio.to_thread(warm_text_encoder,service._embedding._model,384)
        assert warmup["state"]=="ready" and len(warmup["sample_seconds"])>=2
        print(json.dumps({"real_learned_encoder_warmup":warmup,"model":"all-MiniLM-L6-v2","not_gte_performance":True}))
        first=await service.run()
        assert first['inserted']==17 and first['status']=='completed'
        second=await service.run()
        assert second['inserted']==0 and second['status']=='completed'
        pattern='ADL-DEMO-v1-'+service._generator._namespace+'-%'
        async with service._postgres._engine.connect() as db:
            rows=(await db.execute(text('SELECT id,sku,currency,created_at,updated_at FROM products WHERE sku LIKE :pattern'),{'pattern':pattern})).mappings().all()
        assert len(rows)==17 and all(r['currency']=='USD' and r['created_at'].tzinfo and r['updated_at'].tzinfo for r in rows)
        ids={r['id'] for r in rows}
        client=await service._milvus._ensure_client()
        await asyncio.to_thread(client.load_collection,settings.milvus_collection)
        vectors=await asyncio.to_thread(client.query,collection_name=settings.milvus_collection,filter='id in '+json.dumps(sorted(ids)),output_fields=['id','vector'],consistency_level='Strong',limit=100)
        assert {r['id'] for r in vectors}==ids and all(len(r['vector'])==384 for r in vectors)
        search=await asyncio.to_thread(client.search,collection_name=settings.milvus_collection,data=[vectors[0]['vector']],limit=17,output_fields=['id'],search_params={'metric_type':'COSINE'})
        assert search and search[0] and search[0][0]['distance']>0.99
        # Force durable object storage IO, then discard/recreate Milvus compute.
        # etcd and this trial's S3 volume survive, but no Milvus local cache does.
        await asyncio.to_thread(client.flush,settings.milvus_collection)
        await asyncio.to_thread(client.release_collection,settings.milvus_collection)
        await asyncio.to_thread(client.close)
        service._milvus._client=None
        subprocess.run([*compose,'up','-d','--no-deps','--force-recreate','--renew-anon-volumes','--wait','--wait-timeout','240','milvus'],check=True)
        mapped=subprocess.check_output([*compose,'port','milvus','19530'],text=True).strip()
        service._milvus._uri='http://127.0.0.1:'+mapped.rsplit(':',1)[1]
        client=await service._milvus._ensure_client()
        await asyncio.to_thread(client.load_collection,settings.milvus_collection)
        persisted=await asyncio.to_thread(client.query,collection_name=settings.milvus_collection,filter='id in '+json.dumps(sorted(ids)),output_fields=['id','vector'],consistency_level='Strong',limit=100)
        assert {r['id'] for r in persisted}==ids and all(len(r['vector'])==384 for r in persisted)
        recovered=await asyncio.to_thread(client.search,collection_name=settings.milvus_collection,data=[vectors[0]['vector']],limit=17,output_fields=['id'],search_params={'metric_type':'COSINE'})
        assert recovered and recovered[0] and recovered[0][0]['distance']>0.99
        await service._opensearch._client.indices.refresh(index=settings.opensearch_index)
        indexed=await service._opensearch._client.search(index=settings.opensearch_index,body={'query':{'match_all':{}},'size':100})
        assert {int(hit['_id']) for hit in indexed['hits']['hits']}==ids
        print(json.dumps({'result':'passed','postgres_rows':len(rows),'milvus_rows':len(vectors),'opensearch_rows':len(indexed['hits']['hits']),
                          'object_storage':backend,'milvus_recreated_without_local_cache':True,'embedding_dimension':service._embedding.dimension,'model':'all-MiniLM-L6-v2','rerun_inserted':second['inserted'],'scope':'isolated test indexes, not the production GTE model'}))
        # Keep only the unrelated test fixtures in the shared disposable DB.
        async with service._postgres._engine.begin() as db:
            await db.execute(text('DELETE FROM products WHERE sku LIKE :pattern'),{'pattern':pattern})


if __name__=='__main__':
    main()
