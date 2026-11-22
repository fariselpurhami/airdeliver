from unittest.mock import Mock
import logging
import pytest
import seed_ultra_scale as seed
from scripts.inspect_product_collection import inspect_collection


def test_readonly_diagnostic_reports_exact_missing_fields():
    client=Mock();client.has_collection.return_value=True
    client.describe_collection.return_value={'fields':[{'name':'id','type':5,'is_primary':True},{'name':'vector','type':101,'params':{'dim':1536}}]}
    client.list_indexes.return_value=[];client.get_collection_stats.return_value={'row_count':100}
    report=inspect_collection(client,'existing')
    assert report['missing_required_fields']==['category','price','rating']
    assert report['writes_performed'] is False
    client.drop_collection.assert_not_called();client.upsert.assert_not_called();client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_seeder_schema_error_names_mismatch_without_writes():
    settings=seed.Settings(_env_file=None,DATABASE_URI='postgresql+asyncpg://unused/test',RETRY_ATTEMPTS=1)
    repo=seed.MilvusRepository(settings,logging.getLogger('test'),seed.RetryPolicy(settings,logging.getLogger('test')))
    client=Mock();client.has_collection.return_value=True
    client.describe_collection.return_value={'fields':[{'name':'id','type':5,'is_primary':True},{'name':'vector','type':101,'params':{'dim':1536}}]}
    repo._client=client
    with pytest.raises(ValueError,match="missing fields=.*category.*price.*rating"):
        await repo.initialize_schema(1536,False)
    client.drop_collection.assert_not_called();client.create_collection.assert_not_called();client.upsert.assert_not_called()
