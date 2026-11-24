"""Owner-run additive Harrier build. Dry-run is read-only; SQL never written.

Full SQL catalog is preserved, not only the new1000fixtures. Memory is migrated
with source IDs as provenance and original timestamps. Existing GTE indexes are untouched.
"""
import argparse,asyncio,hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if __name__=='__main__':
    pre=argparse.ArgumentParser(add_help=False);pre.add_argument('--profile',choices=['harrier-v1','granite-v1'],default='harrier-v1')
    selected,_=pre.parse_known_args();os.environ['PRODUCT_TEXT_PROFILE']=selected.profile
from app.core.catalog_contract import SPACES
TARGET=SPACES[os.environ.get('PRODUCT_TEXT_PROFILE','harrier-v1')];SOURCE=SPACES['gte-v1']
FIELDS=('id','sku','name','description','category','price','currency','inventory','image','is_active','attributes','tags','rating','created_at','updated_at')

def digest(rows,memory):
    return hashlib.sha256(json.dumps({'products':rows,'memory':memory,'target':TARGET.__dict__},sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()

async def run(args):
    from sqlalchemy import select,text
    from app.db.session import AsyncSessionFactory
    from app.models.product import Product
    from app.core.config import get_core_settings
    from seed_ultra_scale import Settings,RetryPolicy,MilvusRepository,OpenSearchRepository,EmbeddingService,configure_logging
    from pymilvus import MilvusClient,DataType
    core=get_core_settings()
    # Explicit identity prevents stale .env seeder values redirecting writes.
    cfg=Settings(DATABASE_URI=str(core.DATABASE_URI),APP_ENV=core.APP_ENV,
        EMBEDDING_MODEL=TARGET.model,SEED_EMBEDDING_REVISION=TARGET.revision,PRODUCT_TEXT_MODEL_REVISION=TARGET.revision,
        SEED_EMBEDDING_DIMENSION=TARGET.dimension,MILVUS_COLLECTION=TARGET.collection,OPENSEARCH_INDEX=TARGET.search_index,
        MILVUS_ENABLED=True,OPENSEARCH_ENABLED=True,SEED_EMBEDDING_LOCAL_FILES_ONLY=True)
    if core.APP_ENV.lower() in ('prod','production'):raise ValueError('Local migration only')
    async with AsyncSessionFactory() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        products=(await db.execute(select(Product).order_by(Product.id))).scalars().all()
        rows=[{f:getattr(p,f) for f in FIELDS} for p in products]
        await db.rollback()
    if not rows:raise ValueError('Empty SQL catalog')
    client=MilvusClient(uri=cfg.milvus_uri,token=cfg.milvus_token.get_secret_value() if cfg.milvus_token else None)
    memory=[]
    try:
        if client.has_collection(SOURCE.memory_collection):
            iterator=client.query_iterator(collection_name=SOURCE.memory_collection,filter='id >= 0',output_fields=['id','user_id','fact_text','timestamp'],batch_size=100)
            try:
                while True:
                    batch=iterator.next()
                    if not batch:break
                    memory.extend(batch)
            finally:iterator.close()
        memory.sort(key=lambda row:row['id'])
        sha=digest(rows,memory)
        print(json.dumps({'mode':'apply' if args.apply else 'dry_run','sha256':sha,'products':len(rows),
            'fixture_products':sum(r['attributes'].get('_seed_dataset')=='airdeliver-dev-fixtures-v1' for r in rows),
            'memory_records':len(memory),'sql_writes':False,'source_indexes_untouched':True,'target':TARGET.__dict__}),flush=True)
        if not args.apply:return
        if sha!=args.reviewed_sha256:raise ValueError('Review current dryrun SHA before apply')
        if len(rows)!=args.expected_products:raise ValueError('SQL count differs from reviewed count')
        # Refuse target memory leftovers so a changed source cannot leave stale facts.
        if client.has_collection(TARGET.memory_collection):
            count=int(client.get_collection_stats(TARGET.memory_collection).get('row_count',0))
            if count:raise ValueError('Nonempty target memory requires reconciliation; no automatic deletion')
        log=configure_logging('INFO');retry=RetryPolicy(cfg,log)
        milvus=MilvusRepository(cfg,log,retry);search=OpenSearchRepository(cfg,log,retry)
        try:
            embedding=EmbeddingService(cfg,log)
            from app.services.real_catalog_import import sync_import
            totals={'milvus':0,'opensearch':0}
            for start in range(0,len(rows),16):
                result=await sync_import(rows[start:start+16],embedding,milvus,search)
                for k,v in result.items():totals[k]+=v
                print(json.dumps({'products_confirmed':start+len(rows[start:start+16]),'total':len(rows)}),flush=True)
            if not client.has_collection(TARGET.memory_collection):
                schema=client.create_schema(auto_id=True,enable_dynamic_field=True)
                schema.add_field(field_name='id',datatype=DataType.INT64,is_primary=True)
                schema.add_field(field_name='vector',datatype=DataType.FLOAT_VECTOR,dim=TARGET.dimension)
                schema.add_field(field_name='user_id',datatype=DataType.INT64)
                schema.add_field(field_name='fact_text',datatype=DataType.VARCHAR,max_length=8192)
                schema.add_field(field_name='timestamp',datatype=DataType.INT64)
                indexes=client.prepare_index_params();indexes.add_index(field_name='vector',index_type='HNSW',metric_type='COSINE',params={'M':8,'efConstruction':100})
                client.create_collection(collection_name=TARGET.memory_collection,schema=schema,index_params=indexes)
            # Same encoding contract as active memory anchor/recall API.
            for record in memory:
                vector=embedding._model.encode(record['fact_text'],prompt=TARGET.query_prompt,normalize_embeddings=True,convert_to_numpy=True)
                client.insert(collection_name=TARGET.memory_collection,data=[{**{k:v for k,v in record.items() if k!='id'},'source_memory_id':record['id'],'vector':vector.tolist()}])
            client.flush(collection_name=TARGET.collection);client.flush(collection_name=TARGET.memory_collection)
            actual=int(client.get_collection_stats(TARGET.collection).get('row_count',0))
            actual_memory=int(client.get_collection_stats(TARGET.memory_collection).get('row_count',0))
            await search._client.indices.refresh(index=TARGET.search_index)
            os_count=(await search._client.count(index=TARGET.search_index))['count']
            if actual!=len(rows) or actual_memory!=len(memory) or os_count!=len(rows):raise ValueError('Final Milvus counts differ')
            print(json.dumps({'status':'build_complete_not_activated','counts':totals,'milvus_count':actual,'memory_count':actual_memory,'opensearch_count':os_count,'sha256':sha,'old_data_deleted':False}),flush=True)
        finally:await milvus.close();await search.close()
    finally:client.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=['harrier-v1','granite-v1'],default='harrier-v1');p.add_argument('--apply',action='store_true');p.add_argument('--reviewed-sha256');p.add_argument('--expected-products',type=int,default=1100)
    try:asyncio.run(run(p.parse_args()))
    except Exception as exc:
        print(json.dumps({'status':'failed_or_partial','error_type':type(exc).__name__,'action':'Do not activate. Old indexes and SQL untouched. Inspect partial candidate before retry.'}));raise SystemExit(1) from None
