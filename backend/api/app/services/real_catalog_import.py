"""Validated authorised-source import. No fetching, generation, deletion or model calls."""
import hashlib,json,re
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictStr,StrictBool,field_validator,model_validator
from sqlalchemy import select,text
from app.models.product import Product

CATEGORIES={'clothing':'ملابس','accessories':'اكسسورات','electronics':'الكترونيات','makeup':'مكياج','beauty':'تجميل','personal_care':'عنايه','sports':'رياضه'}
# Source: owner message phonemsg-01M84BGYAG1YXF1XJWHM5GYGC5.


def public_https(value):
    import ipaddress
    parsed=urlsplit(value);host=parsed.hostname or ''
    if host=='airdeliver.local' and value=='https://airdeliver.local/dev-fixture':return value
    if parsed.scheme!='https' or not host or '.' not in host or parsed.username or parsed.password or parsed.port not in (None,443):raise ValueError('HTTPS public source required')
    if host.endswith(('.local','.localhost','.internal','.example','.invalid','.test')) or host in ('example.com','example.org','example.net'):raise ValueError('Placeholder/private host')
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise ValueError('LiteralIP not allowed')
    return value

class ImportRow(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    sku:StrictStr=Field(min_length=2,max_length=128)
    name:StrictStr=Field(min_length=3,max_length=255)
    description:StrictStr=Field(min_length=1,max_length=8192)
    category:Literal['clothing','accessories','electronics','makeup','beauty','personal_care','sports']
    price:StrictStr=Field(pattern=r'^(?:0|[1-9]\d{0,7})\.\d{2}$')
    currency:StrictStr=Field(pattern=r'^[A-Z]{3}$')
    inventory:StrictInt=Field(ge=0,le=2147483647)
    image_url:StrictStr=Field(max_length=2048)
    source_url:StrictStr=Field(max_length=2048)
    licence:StrictStr=Field(min_length=3,max_length=500)
    image_licence:StrictStr=Field(min_length=3,max_length=500)
    inventory_verified_at:datetime
    attributes:dict[StrictStr,StrictStr]=Field(default_factory=dict,max_length=32)
    tags:list[StrictStr]=Field(default_factory=list,max_length=20)
    rating:float|None=Field(default=None,ge=0,le=5)

    @field_validator('image_url','source_url')
    @classmethod
    def urls(cls,value):
        if value.startswith('/dev-fixtures/') and re.fullmatch(r'/dev-fixtures/[a-z_]+\.svg',value):return value
        return public_https(value)
    @model_validator(mode='after')
    def provenance(self):
        content=' '.join([self.sku,self.name,self.description,self.source_url,self.image_url,self.licence,self.image_licence,*self.tags,*self.attributes.keys(),*self.attributes.values()])
        if not self.sku.startswith('ADL-DEV-v1-') and re.search(r'(?i)(?:\b(?:demo|dummy|mock|synthetic|placeholder|lorem ipsum|generated product|sample product|test product)\b|ADL-DEMO|picsum\.photos|placehold\.|images\.unsplash\.com)',content):raise ValueError('Synthetic/placeholder evidence rejected')
        if any(k.startswith('_') or len(k)>64 or len(v)>256 for k,v in self.attributes.items()):raise ValueError('Reserved/unbounded attributes')
        now=datetime.now(timezone.utc)
        if self.inventory_verified_at.tzinfo is None or (not self.sku.startswith('ADL-DEV-v1-') and not now-timedelta(days=1)<=self.inventory_verified_at<=now+timedelta(minutes=5)):raise ValueError('Inventory timestamp must be timezone aware and within24hours')
        if Decimal(self.price)<=0:raise ValueError('Actual positive sale price required')
        if any(len(t)>128 for t in self.tags):raise ValueError('Unbounded tag')
        return self

class ImportFile(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:Literal[1]
    source_id:StrictStr=Field(pattern=r'^[a-z0-9][a-z0-9_-]{2,63}$')
    source_kind:Literal['partner_feed','own_inventory','licensed_dataset','dev_fixture']
    authorised_source_url:StrictStr=Field(max_length=2048)
    rights_confirmed:StrictBool
    offers_authorised:StrictBool
    products:list[ImportRow]=Field(min_length=1,max_length=1000)
    @model_validator(mode='after')
    def source(self):
        if self.source_kind=='dev_fixture':
            from app.services.catalog_visibility import fixtures_enabled
            if not fixtures_enabled():raise ValueError('Explicit development fixture flag required')
            if self.source_id!='airdeliver-dev-fixtures-v1' or self.authorised_source_url!='local:airdeliver-dev-fixtures-v1':raise ValueError('Exact fixture source required')
            if any(not r.sku.startswith('ADL-DEV-v1-') or r.source_url!='https://airdeliver.local/dev-fixture' or r.licence!='Synthetic local test data' or r.image_licence!='Original locally generated neutral SVG' or r.image_url!=f'/dev-fixtures/{r.category}.svg' or r.rating is not None for r in self.products):raise ValueError('Invalid fixture provenance/image/rating')
        else:
            public_https(self.authorised_source_url)
            if any(r.sku.startswith('ADL-DEV-v1-') or r.source_url=='https://airdeliver.local/dev-fixture' or r.image_url.startswith('/') or r.source_url.startswith('/') for r in self.products):raise ValueError('Fixtures cannot masquerade as actual inventory')
        if self.rights_confirmed is not True or self.offers_authorised is not True:raise ValueError('Listing and image rights plus actual offer authority required')
        if len({r.sku for r in self.products})!=len(self.products):raise ValueError('DuplicateSKU within file')
        return self

def load_import(path):
    path=Path(path)
    if path.stat().st_size>16*1024*1024:raise ValueError('Import file exceeds16MiB')
    raw=path.read_bytes()
    return ImportFile.model_validate_json(raw),hashlib.sha256(raw).hexdigest()

async def plan_import(db,payload):
    skus=sorted(row.sku for row in payload.products)
    existing={p.sku:p for p in (await db.execute(select(Product).where(Product.sku.in_(skus)).execution_options(populate_existing=True))).scalars().all()}
    for sku,row in existing.items():
        if (row.attributes or {}).get('_import_source_id')!=payload.source_id:
            raise ValueError('SKU owned by another source or legacy catalog; nothing overwritten')
    return existing,{'rows':len(skus),'create':len(set(skus)-existing.keys()),'existing':len(existing),'categories':sorted({r.category for r in payload.products})}

async def persist_import(db,payload):
    # Serialises this importer perSKU, preserves other sources and all demo rows.
    for sku in sorted(r.sku for r in payload.products):
        await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:sku,0))'),{'sku':sku})
    existing,report=await plan_import(db,payload)
    rows=[]
    for item in payload.products:
        attrs={**item.attributes,'_import_source_id':payload.source_id,'_source_url':item.source_url,
            '_licence':item.licence,'_image_licence':item.image_licence,'_inventory_verified_at':item.inventory_verified_at.isoformat(),
            '_authorised_source_url':payload.authorised_source_url,'_source_kind':payload.source_kind}
        if payload.source_kind=='dev_fixture':attrs['_seed_dataset']='airdeliver-dev-fixtures-v1'
        values=dict(sku=item.sku,name=item.name,description=item.description,category=item.category,price=Decimal(item.price),currency=item.currency,
            inventory=item.inventory,image=item.image_url,is_active=True,attributes=attrs,tags=item.tags,rating=item.rating)
        product=existing.get(item.sku)
        if product is None:product=Product(**values);db.add(product)
        else:
            for key,value in values.items():setattr(product,key,value)
        rows.append(product)
    await db.flush()
    snapshots=[{field:getattr(row,field) for field in ('id','sku','name','description','category','price','currency','inventory','image','is_active','attributes','tags','rating','created_at','updated_at')} for row in rows]
    await db.commit()
    return snapshots,report

async def sync_import(snapshots,embedding,milvus,opensearch):
    """Reuse reviewed existing sinks, never generator/fresh-start/drop/run."""
    from types import SimpleNamespace
    from seed_ultra_scale import ProductVector
    products=[SimpleNamespace(**{**row,'rating':row['rating'] if row['rating'] is not None else 0.}) for row in snapshots] # Index schema uses0 for unrated; SQL remainsNULL.
    embedding_rows=[SimpleNamespace(**{**p.__dict__,'attributes':{k:v for k,v in p.attributes.items() if not k.startswith(('_','fixture_')) and k!='image_kind'}}) for p in products]
    vectors=await embedding.embed_products(embedding_rows)
    if len(vectors)!=len(products):raise ValueError('Embedding identity/count mismatch')
    vector_rows=[ProductVector(product_id=p.id,vector=vector,price=float(p.price),rating=p.rating if p.rating is not None else 0.,category=p.category,attributes=p.attributes) for p,vector in zip(products,vectors)]
    await milvus.initialize_schema(embedding.dimension,drop_existing=False)
    await opensearch.initialize_schema(embedding.dimension,drop_existing=False)
    m=await milvus.insert_batch(products,vector_rows)
    o=await opensearch.insert_batch(products,vector_rows)
    if m!=len(products) or o!=len(products):raise RuntimeError('Indexes did not confirm every row')
    return {'milvus':m,'opensearch':o}
