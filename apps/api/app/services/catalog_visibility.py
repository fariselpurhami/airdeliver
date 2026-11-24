"""Real-only customer catalog policy. Retains stored history and diagnostics."""
from sqlalchemy import func

FIXTURE_DATASET="airdeliver-dev-fixtures-v1"

def fixtures_enabled():
    from app.core.config import get_core_settings
    try:
        settings=get_core_settings()
        return settings.APP_ENV=="development" and settings.AIRDELIVER_DEV_FIXTURES
    except Exception:return False

def is_dev_fixture(product):
    attrs=product.get("attributes",{}) if isinstance(product,dict) else getattr(product,"attributes",{})
    sku=product.get("sku","") if isinstance(product,dict) else getattr(product,"sku","")
    return (isinstance(attrs,dict) and attrs.get("_seed_dataset")==FIXTURE_DATASET) or str(sku).startswith("ADL-DEV-v1-")

def is_catalog_hidden(product):
    return is_synthetic(product) and not (fixtures_enabled() and is_dev_fixture(product))



def is_synthetic(product):
    if isinstance(product,dict):
        attrs=product.get('attributes',{});sku=product.get('sku','')
    else:
        attrs=getattr(product,'attributes',{});sku=getattr(product,'sku','')
    return is_dev_fixture(product) or (isinstance(attrs,dict) and attrs.get('_seed_dataset')=='airdeliver-demo-v1') or (isinstance(sku,str) and sku.startswith('ADL-DEMO-v1-'))


def real_catalog_predicates(product):
    return (func.coalesce(product.attributes.op('->>')('_seed_dataset'),'')!='airdeliver-demo-v1',
        ~product.sku.like('ADL-DEMO-v1-%'),
        *(() if fixtures_enabled() else (func.coalesce(product.attributes.op('->>')('_seed_dataset'),'')!=FIXTURE_DATASET,~product.sku.like('ADL-DEV-v1-%'))))
