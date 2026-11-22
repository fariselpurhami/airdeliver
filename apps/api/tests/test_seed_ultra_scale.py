"""Deterministic demo data and real PostgreSQL persistence contracts."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import logging
import math
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
import seed_ultra_scale as seed


def settings(**overrides):
    return seed.Settings(_env_file=None, **{
        'DATABASE_URI':os.environ.get('TEST_POSTGRES_DSN','postgresql+asyncpg://unused/airdeliver_test_seed'),
        'MILVUS_ENABLED':False,'OPENSEARCH_ENABLED':False,'RETRY_ATTEMPTS':1,
        'APP_ENV':'development',**overrides})


def test_generation_is_deterministic_across_batches_and_resume_offsets():
    all_rows=seed.ProductGenerator(97).generate_batch(1,100,100)
    resumed=seed.ProductGenerator(97).generate_batch(51,50,100)
    assert [p.model_dump() for p in all_rows[50:]]==[p.model_dump() for p in resumed]
    chunks=[]
    for offset in range(1,101,7):
        chunks+=seed.ProductGenerator(97).generate_batch(offset,7,100)
    assert all_rows==chunks
    assert len({p.sku for p in all_rows})==100
    assert all(p.currency=='USD' and p.created_at.tzinfo and p.price.as_tuple().exponent==-2 for p in all_rows)
    assert all('synthetic test data' in p.description and 'Demo' in p.tags for p in all_rows)
    assert seed.ProductGenerator(98).generate_batch(1,1,1)[0].sku!=all_rows[0].sku


def test_settings_accept_compose_aliases_and_use_bounded_mac_defaults():
    value=settings(SEED_TARGET_COUNT=123,SEED_BATCH_SIZE=7)
    assert (value.target_count,value.batch_size)==(123,7)
    assert value.embedding_encode_batch_size==1 and value.postgres_pool_size==2 and value.postgres_max_overflow==0
    assert value.milvus_collection=='airdeliver_products_sota_v4'
    with pytest.raises(ValueError,match='1536'):
        settings(MILVUS_ENABLED=True,SEED_EMBEDDING_DIMENSION=384)
    with pytest.raises(ValueError,match='disabled in production'):
        settings(APP_ENV='production')
    with pytest.raises(ValueError):
        settings(SEED_BATCH_SIZE=100000)


@pytest.mark.parametrize('vector',[[],[math.nan],[math.inf],[0,0]])
def test_invalid_vectors_are_rejected(vector):
    with pytest.raises(ValueError):
        seed.ProductVector(product_id=1,vector=vector,price=1,rating=4,category='test',attributes={})


def test_vector_pairing_never_silently_truncates():
    product=seed.ProductGenerator(1).generate_batch(1,1,1)[0]
    with pytest.raises(ValueError,match='length mismatch'):
        seed.SeederService._build_product_vectors([product],[])
    with pytest.raises(ValueError,match='Mixed'):
        seed.SeederService._build_product_vectors([product,product],[[1,0],[1,0,0]])


@pytest.mark.asyncio
async def test_milvus_reuses_api_collection_and_refuses_wrong_dimensions_without_deletion():
    value=settings(MILVUS_ENABLED=True)
    repository=seed.MilvusRepository(value,logging.getLogger('seed-test'),seed.RetryPolicy(value,logging.getLogger('seed-test')))
    client=Mock()
    client.has_collection.return_value=True
    client.describe_collection.return_value={'fields':[{'name':'vector','params':{'dim':'384'}}]}
    repository._client=client
    with pytest.raises(ValueError,match='dimension'):
        await repository.initialize_schema(1536,False)
    client.drop_collection.assert_not_called()
    with pytest.raises(ValueError,match='Destructive'):
        await repository.initialize_schema(1536,True)
    client.drop_collection.assert_not_called()
    await repository.close()
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_milvus_replays_are_upserts_and_check_confirmed_count():
    value=settings(MILVUS_ENABLED=True)
    repository=seed.MilvusRepository(value,logging.getLogger('seed-test'),seed.RetryPolicy(value,logging.getLogger('seed-test')))
    client=Mock(); client.upsert.return_value={'upsert_count':1}; repository._client=client
    product=seed.ProductGenerator(1).generate_batch(1,1,1)[0]
    vectors=seed.SeederService._build_product_vectors([product],[[1.0]+[0.0]*1535])
    assert await repository.insert_batch([product],vectors)==1
    assert await repository.insert_batch([product],vectors)==1
    assert client.upsert.call_count==2
    client.insert.assert_not_called()
    client.upsert.return_value={'upsert_count':0}
    with pytest.raises(RuntimeError,match='confirm'):
        await repository.insert_batch([product],vectors)
    await repository.close()


@pytest.mark.asyncio
async def test_opensearch_refuses_wrong_dimension_and_never_deletes_an_index():
    value=settings(OPENSEARCH_ENABLED=True)
    repository=seed.OpenSearchRepository(value,logging.getLogger('seed-test'),seed.RetryPolicy(value,logging.getLogger('seed-test')))
    await repository._client.close()
    client=AsyncMock(); repository._client=client
    client.indices.exists.return_value=True
    client.indices.get_mapping.return_value={'airdeliver_products':{'mappings':{'properties':{'vector':{'type':'knn_vector','dimension':384}}}}}
    with pytest.raises(ValueError,match='dimension'):
        await repository.initialize_schema(1536,False)
    client.indices.delete.assert_not_called()
    with pytest.raises(ValueError,match='Destructive'):
        await repository.initialize_schema(1536,True)
    client.indices.delete.assert_not_called()
    await repository.close()


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_DSN'),reason='Real migrated PostgreSQL required')
async def test_real_postgres_thousand_rows_rerun_existing_data_and_auto_ids():
    assert make_url(os.environ['TEST_POSTGRES_DSN']).database.startswith('airdeliver_test_')
    random_seed=uuid.uuid4().int%(2**60)
    value=settings(SEED_RANDOM_SEED=random_seed,SEED_TARGET_COUNT=1000)
    logger=logging.getLogger('seed-real-postgres')
    repository=seed.PostgresRepository(value,logger,seed.RetryPolicy(value,logger))
    generator=seed.ProductGenerator(random_seed)
    pattern=f'ADL-DEMO-v1-{generator._namespace}-%'
    sentinel='seed-existing-'+uuid.uuid4().hex
    try:
        await repository.initialize_schema()
        async with repository._engine.begin() as db:
            await db.execute(text("INSERT INTO products(id,sku,name,description,price,currency,inventory,category,tags,attributes,is_active,created_at,updated_at) VALUES(2000000000,:sku,'Existing catalog','Preserve me',19.99,'USD',31,'existing','[]','{}',true,now(),now())"),{'sku':sentinel})
        service=seed.SeederService(value,logger,repository,None,None,None,generator)
        first=await service.run()
        assert first['processed']==1000 and first['inserted']==1000
        async with repository._engine.begin() as db:
            rows=(await db.execute(text('SELECT id,sku,price,currency,attributes,tags,created_at,updated_at FROM products WHERE sku LIKE :pattern ORDER BY sku'),{'pattern':pattern})).mappings().all()
            assert len(rows)==1000 and len({r['id'] for r in rows})==1000
            assert all(r['currency']=='USD' and r['created_at'].tzinfo and isinstance(r['attributes'],dict) and isinstance(r['tags'],list) and r['price'].as_tuple().exponent==-2 for r in rows)
            before=[dict(r) for r in rows]
            await db.execute(text('UPDATE products SET inventory=17 WHERE id=:id'),{'id':rows[0]['id']})
        value.batch_size=7
        again=await seed.SeederService(value,logger,repository,None,None,None,seed.ProductGenerator(random_seed)).run()
        assert again['inserted']==0 and again['processed']==1000
        async with repository._engine.connect() as db:
            after=(await db.execute(text('SELECT id,sku,price,currency,attributes,tags,created_at,updated_at FROM products WHERE sku LIKE :pattern ORDER BY sku'),{'pattern':pattern})).mappings().all()
            assert [dict(r) for r in after]==before
            assert (await db.execute(text('SELECT inventory FROM products WHERE id=:id'),{'id':rows[0]['id']})).scalar_one()==17
            assert (await db.execute(text('SELECT name,price,inventory FROM products WHERE sku=:sku'),{'sku':sentinel})).one()==('Existing catalog',Decimal('19.99'),31)
    finally:
        async with repository._engine.begin() as db:
            await db.execute(text('DELETE FROM products WHERE sku LIKE :pattern OR sku=:sku'),{'pattern':pattern,'sku':sentinel})
        await repository.close()


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_DSN'),reason='Real migrated PostgreSQL required')
async def test_real_postgres_replay_repairs_a_failed_sink_using_database_ids():
    assert make_url(os.environ['TEST_POSTGRES_DSN']).database.startswith('airdeliver_test_')
    random_seed=uuid.uuid4().int%(2**60)
    value=settings(MILVUS_ENABLED=True,SEED_RANDOM_SEED=random_seed,SEED_TARGET_COUNT=17)
    logger=logging.getLogger('seed-repair'); repository=seed.PostgresRepository(value,logger,seed.RetryPolicy(value,logger))
    generator=seed.ProductGenerator(random_seed); pattern=f'ADL-DEMO-v1-{generator._namespace}-%'
    embedding=SimpleNamespace(dimension=1536,embed_products=AsyncMock(side_effect=lambda products:asyncio.sleep(0,result=[[1.0]+[0.0]*1535 for _ in products])))
    async def embed(products):
        return [[1.0]+[0.0]*1535 for _ in products]
    embedding.embed_products=AsyncMock(side_effect=embed)
    sink=SimpleNamespace(initialize_schema=AsyncMock(),insert_batch=AsyncMock(side_effect=RuntimeError('test transport failure')))
    try:
        with pytest.raises(RuntimeError,match='transport failure'):
            await seed.SeederService(value,logger,repository,sink,None,embedding,generator).run()
        seen=[]
        async def save(products,vectors):
            assert [p.id for p in products]==[v.product_id for v in vectors]
            seen.extend(p.id for p in products)
            return len(products)
        sink.insert_batch=AsyncMock(side_effect=save)
        result=await seed.SeederService(value,logger,repository,sink,None,embedding,seed.ProductGenerator(random_seed)).run()
        assert result['inserted']==1 and len(seen)==17
        async with repository._engine.connect() as db:
            actual=set((await db.execute(text('SELECT id FROM products WHERE sku LIKE :pattern'),{'pattern':pattern})).scalars().all())
        assert actual==set(seen)
        assert all(call.kwargs.get('drop_existing') is False for call in sink.initialize_schema.call_args_list)
    finally:
        async with repository._engine.begin() as db:
            await db.execute(text('DELETE FROM products WHERE sku LIKE :pattern'),{'pattern':pattern})
        await repository.close()


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get('TEST_SEED_REAL_EMBEDDINGS')!='1' or not os.environ.get('TEST_SEED_EMBEDDING_MODEL_PATH'),reason='Explicit offline model smoke test')
async def test_real_embedding_model_uses_sentence_dimension_and_finite_normalized_vectors():
    cache=Path(os.environ['TEST_SEED_EMBEDDING_MODEL_PATH'])
    assert cache.exists()
    value=settings(EMBEDDING_MODEL=str(cache),SEED_EMBEDDING_DIMENSION=384)
    service=seed.EmbeddingService(value,logging.getLogger('real-embedding-smoke'))
    products=seed.ProductGenerator(3).generate_batch(1,2,2)
    vectors=await service.embed_products(products)
    assert service.dimension==384 and len(vectors)==2
    assert all(len(v)==384 and all(math.isfinite(x) for x in v) and abs(sum(x*x for x in v)-1)<0.001 for v in vectors)


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_DSN'),reason='Real migrated PostgreSQL required')
async def test_actual_cli_postgres_only_and_rerun_are_explicit(tmp_path):
    import subprocess
    import sys
    import json
    assert make_url(os.environ['TEST_POSTGRES_DSN']).database.startswith('airdeliver_test_')
    random_seed=uuid.uuid4().int%(2**60)
    env={**os.environ,'APP_ENV':'development','DATABASE_URI':os.environ['TEST_POSTGRES_DSN'],
         'MILVUS_ENABLED':'false','OPENSEARCH_ENABLED':'false','SEED_TARGET_COUNT':'7','SEED_BATCH_SIZE':'3','SEED_RANDOM_SEED':str(random_seed)}
    repository=seed.PostgresRepository(settings(),logging.getLogger('cli-proof'),seed.RetryPolicy(settings(),logging.getLogger('cli-proof')))
    pattern='ADL-DEMO-v1-'+seed.ProductGenerator(random_seed)._namespace+'-%'
    try:
        summaries=[]
        for _ in range(2):
            result=subprocess.run([sys.executable,str(Path(seed.__file__))],env=env,cwd=tmp_path,capture_output=True,text=True,timeout=45)
            assert result.returncode==0,result.stderr
            entries=[json.loads(line) for line in result.stderr.splitlines() if line.startswith('{')]
            summaries.append(next(line for line in entries if line.get('event')=='seeding_completed'))
        assert [entry['inserted'] for entry in summaries]==[7,0]
        assert all(entry['milvus']=='disabled' and entry['opensearch']=='disabled' for entry in summaries)
    finally:
        async with repository._engine.begin() as db:
            await db.execute(text('DELETE FROM products WHERE sku LIKE :pattern'),{'pattern':pattern})
        await repository.close()


@pytest.mark.asyncio
async def test_soft_index_initialization_failure_cannot_be_reported_as_complete():
    value=settings(MILVUS_ENABLED=True,FAIL_ON_MILVUS_ERROR=False,SEED_TARGET_COUNT=1)
    async def persisted(products):
        return list(products),len(products)
    database=SimpleNamespace(initialize_schema=AsyncMock(),persist_batch=AsyncMock(side_effect=persisted))
    sink=SimpleNamespace(initialize_schema=AsyncMock(side_effect=RuntimeError('schema unavailable')),insert_batch=AsyncMock(return_value=1))
    embedding=SimpleNamespace(dimension=1536,embed_products=AsyncMock(return_value=[[1.0]+[0.0]*1535]))
    service=seed.SeederService(value,logging.getLogger('degraded-test'),database,sink,None,embedding,seed.ProductGenerator(1))
    with pytest.raises(RuntimeError,match='configured indexes failed'):
        await service.run()


def test_database_validation_errors_do_not_echo_passwords():
    password='test-only-must-not-be-echoed'
    with pytest.raises(ValueError) as error:
        settings(DATABASE_URI='postgresql+psycopg://test:'+password+'@localhost/airdeliver_test_wrong_driver')
    assert password not in str(error.value)


def test_api_and_seeder_share_text_model_dimension_collection_and_default_pin():
    from app.core.catalog_contract import PRODUCT_TEXT_MODEL_NAME,PRODUCT_TEXT_MODEL_DIMENSION,PRODUCT_TEXT_COLLECTION,DEFAULT_PRODUCT_TEXT_MODEL_REVISION
    from app.services.ai_commerce_engine import AICommerceEngine,PRODUCT_TEXT_MODEL
    value=settings()
    assert value.embedding_model==PRODUCT_TEXT_MODEL.name==PRODUCT_TEXT_MODEL_NAME
    assert value.embedding_dimension==PRODUCT_TEXT_MODEL.dimension==AICommerceEngine.SCHEMA_CONFIG['product_text'].dim==PRODUCT_TEXT_MODEL_DIMENSION
    assert value.milvus_collection==AICommerceEngine.SCHEMA_CONFIG['product_text'].name==PRODUCT_TEXT_COLLECTION
    assert value.embedding_revision==DEFAULT_PRODUCT_TEXT_MODEL_REVISION
