"""Read-only product-vector schema diagnostic. Does not load an embedding model."""
import json
import os
from pymilvus import MilvusClient
from app.core.catalog_contract import PRODUCT_TEXT_COLLECTION,PRODUCT_TEXT_MODEL_DIMENSION


def inspect_collection(client,name):
    if not client.has_collection(name):
        return {'collection':name,'exists':False,'writes_performed':False}
    description=client.describe_collection(name)
    fields=description.get('fields',[])
    indexes=[client.describe_index(name,index) for index in client.list_indexes(name)]
    return {
        'collection':name,'exists':True,'writes_performed':False,
        'auto_id':description.get('auto_id'),
        'enable_dynamic_field':description.get('enable_dynamic_field'),
        'fields':[{'name':f.get('name'),'type':int(f.get('type',0)),
                   'is_primary':f.get('is_primary',False),'params':f.get('params',{})} for f in fields],
        'missing_required_fields':sorted({'id','vector','price','rating','category'}-{f.get('name') for f in fields}),
        'expected_dimension':PRODUCT_TEXT_MODEL_DIMENSION,
        'indexes':[{'field_name':x.get('field_name'),'metric_type':x.get('metric_type'),'index_type':x.get('index_type')} for x in indexes],
        'statistics':client.get_collection_stats(name),
    }


def main():
    client=MilvusClient(uri=os.environ.get('MILVUS_URI','http://milvus:19530'),token=os.environ.get('MILVUS_TOKEN') or None)
    try:print(json.dumps(inspect_collection(client,os.environ.get('MILVUS_COLLECTION') or PRODUCT_TEXT_COLLECTION),indent=2))
    finally:client.close()


if __name__=='__main__':main()
