"""Product image alias contract shared by storefront endpoints."""
from urllib.parse import urlsplit

FALLBACK='/images/catalog-placeholder.svg'


def serialize_product(product):
    row=product.model_dump()
    value=row.get('image_url') or row.get('image')
    valid=False
    if isinstance(value,str) and len(value)<=2048 and not any(ord(c)<32 for c in value):
        parsed=urlsplit(value)
        valid=(value.startswith('/') and not value.startswith('//') and '\\' not in value) or (
            parsed.scheme in {'http','https'} and bool(parsed.hostname) and not parsed.username and not parsed.password)
    row['image_url']=value if valid else FALLBACK
    return row
