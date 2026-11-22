"""Explicit maintenance repair for the known empty worker-created rating mismatch."""
import argparse
import json
import os
from pymilvus import MilvusClient,DataType
from app.core.catalog_contract import PRODUCT_TEXT_COLLECTION,PRODUCT_TEXT_MODEL_DIMENSION
from scripts.inspect_product_collection import inspect_collection


def repair(client,name,*,apply=False,writers_stopped=False):
    report=inspect_collection(client,name)
    if not apply:return report
    if not writers_stopped:raise ValueError('Stop all API/worker/seeder writers before applying')
    if name!=PRODUCT_TEXT_COLLECTION:raise ValueError('Only the exact shared product text collection is allowed')
    fields={f['name']:f for f in report.get('fields',[])}
    if (set(fields)!={'id','vector','price','category'} or report.get('auto_id') is not False
            or report.get('enable_dynamic_field') is not True
            or not fields.get('id',{}).get('is_primary')
            or fields['id']['type']!=int(DataType.INT64)
            or fields['vector']['type']!=int(DataType.FLOAT_VECTOR)
            or int(fields['vector']['params'].get('dim',0))!=PRODUCT_TEXT_MODEL_DIMENSION
            or fields['price']['type']!=int(DataType.FLOAT)
            or fields['category']['type']!=int(DataType.VARCHAR)
            or int(fields['category']['params'].get('max_length',0))!=128):
        raise ValueError('Refusing repair: schema is not the exact known missing-rating worker schema')
    if not any(x['field_name']=='vector' and x['metric_type']=='COSINE' for x in report['indexes']):
        raise ValueError('Refusing repair: vector index is not COSINE')
    if int(report['statistics'].get('row_count',-1))!=0:
        raise ValueError('Refusing repair: collection is not proven empty')
    client.flush(collection_name=name)
    client.load_collection(collection_name=name)
    count=client.query(collection_name=name,filter='',output_fields=['count(*)'],consistency_level='Strong')
    if count!=[{'count(*)':0}]:raise ValueError('Refusing repair: strong row count is not exactly zero')
    # Maintenance attestation is required: Milvus has no atomic compare-count/drop.
    # No other writers may run between the last check and this explicit operation.
    schema=MilvusClient.create_schema(auto_id=False,enable_dynamic_field=True)
    schema.add_field('id',DataType.INT64,is_primary=True)
    schema.add_field('vector',DataType.FLOAT_VECTOR,dim=PRODUCT_TEXT_MODEL_DIMENSION)
    schema.add_field('price',DataType.FLOAT)
    schema.add_field('rating',DataType.FLOAT)
    schema.add_field('category',DataType.VARCHAR,max_length=128)
    indexes=client.prepare_index_params()
    indexes.add_index(field_name='vector',metric_type='COSINE',index_type='HNSW',params={'M':16,'efConstruction':200})
    client.drop_collection(collection_name=name)
    # If creation fails, rerunning the ordinary seeder/API bootstrap creates the
    # canonical missing collection. Never retry a drop against a newly filled one.
    client.create_collection(collection_name=name,schema=schema,index_params=indexes)
    after=inspect_collection(client,name)
    if after['missing_required_fields']:raise RuntimeError('Recreated collection failed schema verification')
    return {**after,'writes_performed':True,'repair':'empty_missing_rating_recreated'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection',required=True)
    p.add_argument('--apply-empty-repair',action='store_true')
    p.add_argument('--confirm-writers-stopped',action='store_true')
    a=p.parse_args()
    client=MilvusClient(uri=os.environ.get('MILVUS_URI','http://milvus:19530'),token=os.environ.get('MILVUS_TOKEN') or None)
    try:print(json.dumps(repair(client,a.collection,apply=a.apply_empty_repair,writers_stopped=a.confirm_writers_stopped),indent=2))
    finally:client.close()


if __name__=='__main__':main()
