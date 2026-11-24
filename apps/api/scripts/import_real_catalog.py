"""Owner-run authorised bulk import. Default dryrun. Never fetches product sources."""
import argparse,asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.real_catalog_import import load_import,plan_import,persist_import,sync_import

async def run(args):
    payload,digest=load_import(args.file)
    from app.db.session import AsyncSessionFactory
    async with AsyncSessionFactory() as db:
        _,plan=await plan_import(db,payload)
        if not args.apply:
            await db.rollback();print(json.dumps({'mode':'dry_run','sha256':digest,'plan':plan,'writes':False,'source_truth':'Rights, image identity and actual stock are owner-attested, not automatically verified.'}));return
        if args.reviewed_sha256!=digest:raise ValueError('Run dryrun and review exactSHA beforeapply')
        snapshots,plan=await persist_import(db,payload)
    # SQL commit is durable before index work. Failure is explicitly partial,
    # rerunning exactfile repairs indexes with stableSKU/SQLid, no duplicate rows.
    print(json.dumps({'sql_committed':True,'sha256':digest,'plan':plan,'index_status':'pending'}),flush=True)
    from seed_ultra_scale import Settings,RetryPolicy,MilvusRepository,OpenSearchRepository,EmbeddingService,configure_logging
    from app.core.config import get_core_settings
    core=get_core_settings()
    settings=Settings(DATABASE_URI=str(core.DATABASE_URI),APP_ENV=core.APP_ENV,MILVUS_ENABLED=True,OPENSEARCH_ENABLED=True)
    logger=configure_logging('INFO');retry=RetryPolicy(settings,logger)
    milvus=MilvusRepository(settings,logger,retry);opensearch=OpenSearchRepository(settings,logger,retry)
    try:
        embedding=EmbeddingService(settings,logger)
        counts={ 'milvus':0,'opensearch':0 }
        for start in range(0,len(snapshots),32):
            result=await sync_import(snapshots[start:start+32],embedding,milvus,opensearch)
            for key,value in result.items():counts[key]+=value
        print(json.dumps({'sql_committed':True,'index_status':'confirmed','counts':counts,'sha256':digest}))
    finally:await milvus.close();await opensearch.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--file',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--reviewed-sha256');args=parser.parse_args()
    try:asyncio.run(run(args))
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'status':'failed_or_partial','message':'No automatic rollback or deletion. If SQL committed was printed, inspect state and rerun the same reviewed source to reconcile indexes. Error values withheld.'}));raise SystemExit(1) from None
