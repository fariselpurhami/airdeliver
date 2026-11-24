"""Real-only customer catalog policy. Retains stored history and diagnostics."""
from sqlalchemy import func


def is_synthetic(product):
    if isinstance(product,dict):
        attrs=product.get('attributes',{});sku=product.get('sku','')
    else:
        attrs=getattr(product,'attributes',{});sku=getattr(product,'sku','')
    return (isinstance(attrs,dict) and attrs.get('_seed_dataset')=='airdeliver-demo-v1') or (isinstance(sku,str) and sku.startswith('ADL-DEMO-v1-'))


def real_catalog_predicates(product):
    return (func.coalesce(product.attributes.op('->>')('_seed_dataset'),'')!='airdeliver-demo-v1',
        ~product.sku.like('ADL-DEMO-v1-%'))
