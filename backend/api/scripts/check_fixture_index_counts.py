"""Owner-run read-only count reconciliation. No embedding, schema or index writes."""
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

async def main():
    from sqlalchemy import select
    from app.models.product import Product
    from app.db.session import AsyncSessionFactory
    from app.core.config import get_core_settings
    from tools.seed_ultra_scale import Settings, RetryPolicy, MilvusRepository, OpenSearchRepository, configure_logging
    async with AsyncSessionFactory() as db:
        ids=list((await db.execute(select(Product.id).where(Product.attributes.op('->>')('_seed_dataset')=='airdeliver-dev-fixtures-v1'))).scalars())
        await db.rollback()
    core=get_core_settings()
    settings=Settings(DATABASE_URI=str(core.DATABASE_URI),APP_ENV=core.APP_ENV,MILVUS_ENABLED=True,OPENSEARCH_ENABLED=True)
    logger=configure_logging('WARNING');retry=RetryPolicy(settings,logger)
    milvus=MilvusRepository(settings,logger,retry);search=OpenSearchRepository(settings,logger,retry)
    try:
        client=await milvus._ensure_client()
        result=await asyncio.to_thread(client.query,collection_name=settings.milvus_collection,filter='id in '+json.dumps(ids) if ids else 'id < 0',output_fields=['count(*)'],consistency_level='Strong')
        count=await search._client.count(index=settings.opensearch_index,body={'query':{'terms':{'id':ids}}}) if ids else {'count':0}
        print(json.dumps({'writes':False,'fixture_sql':len(ids),'fixture_milvus':int(result[0]['count(*)']),'fixture_opensearch_search_visible':count['count'],'expected':1000,'caveat':'OpenSearch refresh can lag30seconds. Counts do not prove retrieval relevance or vector quality.'}))
    finally:
        await milvus.close();await search.close()
if __name__=='__main__':asyncio.run(main())
