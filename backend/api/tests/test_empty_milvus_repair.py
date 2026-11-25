from unittest.mock import Mock
import pytest
from scripts.repair_empty_product_collection import repair
from app.core.catalog_contract import PRODUCT_TEXT_COLLECTION as NAME


def client():
    c=Mock();c.has_collection.return_value=True
    fields=[{'name':'id','type':5,'is_primary':True},{'name':'vector','type':101,'params':{'dim':1536}},
            {'name':'price','type':10},{'name':'category','type':21,'params':{'max_length':128}}]
    old={'auto_id':False,'enable_dynamic_field':True,'fields':fields}
    new={**old,'fields':fields+[{'name':'rating','type':10}]}
    c.describe_collection.side_effect=[old,new]
    c.list_indexes.return_value=['vector'];c.describe_index.return_value={'field_name':'vector','metric_type':'COSINE','index_type':'HNSW'}
    c.get_collection_stats.return_value={'row_count':0};c.query.return_value=[{'count(*)':0}]
    return c


def test_dry_run_never_drops():
    c=client();assert repair(c,NAME)['missing_required_fields']==['rating'];c.drop_collection.assert_not_called()


@pytest.mark.parametrize('case',['writers','nonempty','strong_count','name','schema'])
def test_repair_refuses_unproven_or_nonempty_collection(case):
    c=client();name=NAME;writers=True
    if case=='writers':writers=False
    if case=='nonempty':c.get_collection_stats.return_value={'row_count':1}
    if case=='strong_count':c.query.return_value=[{'count(*)':1}]
    if case=='name':name='another_collection'
    if case=='schema':c.describe_collection.side_effect=None;c.describe_collection.return_value={'fields':[]}
    with pytest.raises(ValueError):repair(c,name,apply=True,writers_stopped=writers)
    c.drop_collection.assert_not_called()


def test_only_explicit_known_empty_repair_drops_once_and_checks_new_schema():
    c=client();result=repair(c,NAME,apply=True,writers_stopped=True)
    assert result['missing_required_fields']==[] and result['writes_performed'] is True
    c.drop_collection.assert_called_once_with(collection_name=NAME)
    c.create_collection.assert_called_once()


def test_worker_product_bootstrap_includes_rating():
    from app.services.orchestration import worker_entrypoint as worker
    c=Mock();c.has_collection.return_value=False
    worker.WorkerRuntime.ensure_milvus_schema(c)
    text=c.create_collection.call_args_list[0].kwargs['schema'].to_dict()
    assert 'rating' in {f['name'] for f in text['fields']}
