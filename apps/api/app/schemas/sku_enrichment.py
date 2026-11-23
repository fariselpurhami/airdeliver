"""Reviewed SKU evidence contract. Validation is not verification of a source."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictRecord(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class Evidence(StrictRecord):
    evidence_id: str=Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')
    source_type: Literal['manufacturer','merchant','lab_test','review_platform','synthetic']
    source_url: HttpUrl
    source_title: str=Field(min_length=1,max_length=200)
    captured_at: datetime
    locator: str=Field(min_length=1,max_length=200)
    supporting_excerpt: str=Field(min_length=1,max_length=2000)
    content_sha256: str=Field(pattern=r'^[a-f0-9]{64}$')
    license_or_permission: str=Field(min_length=1,max_length=200)
    @model_validator(mode='after')
    def timezone(self):
        if self.captured_at.tzinfo is None:raise ValueError('Evidence timestamp needs timezone')
        return self


class Review(StrictRecord):
    status: Literal['draft','rejected','approved']
    reviewer: str|None=None
    reviewed_at: datetime|None=None
    notes: str=Field(max_length=1000)
    @model_validator(mode='after')
    def approved(self):
        if self.status=='approved' and (not self.reviewer or not self.reviewed_at or self.reviewed_at.tzinfo is None):
            raise ValueError('Approved review needs reviewer and timezone-aware timestamp')
        return self


class Claim(StrictRecord):
    value: str=Field(min_length=1,max_length=2000)
    evidence_ids: list[str]=Field(min_length=1,max_length=20)


class SizeFit(StrictRecord):
    size_system: str=Field(min_length=1,max_length=60)
    available_sizes: list[str]=Field(min_length=1,max_length=100)
    fit_notes: str=Field(min_length=1,max_length=500)
    evidence_ids: list[str]=Field(min_length=1,max_length=20)


class Rating(StrictRecord):
    value: Decimal=Field(ge=0,le=5)
    count: int=Field(ge=1)
    scale: Literal[5]
    evidence_ids: list[str]=Field(min_length=1,max_length=20)


class Relation(StrictRecord):
    kind: Literal['complement','alternative','compatible','incompatible']
    target_sku: str=Field(min_length=1,max_length=128)
    scope: str=Field(min_length=1,max_length=500)
    evidence_ids: list[str]=Field(min_length=1,max_length=20)
    review: Review


class ProductEnrichment(StrictRecord):
    sku: str=Field(min_length=1,max_length=128)
    synthetic: bool
    authoritative_description: Claim|None
    material: Claim|None
    style: Claim|None
    use: Claim|None
    size_fit: SizeFit|None
    compatibility: list[Relation]=Field(max_length=100)
    rating: Rating|None
    relations: list[Relation]=Field(max_length=100)
    evidence: list[Evidence]=Field(min_length=1,max_length=100)
    review: Review
    @model_validator(mode='after')
    def references(self):
        if any(r.kind not in {'compatible','incompatible'} for r in self.compatibility):
            raise ValueError('Compatibility section requires compatibility relation kinds')
        if any(r.kind not in {'complement','alternative'} for r in self.relations):
            raise ValueError('Relations section requires complement or alternative kinds')
        ids=[e.evidence_id for e in self.evidence]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate evidence identifiers')
        claims=[getattr(self,k) for k in ('authoritative_description','material','style','use','size_fit','rating')]
        for claim in [c for c in claims if c]+self.compatibility+self.relations:
            if not set(claim.evidence_ids)<=set(ids):raise ValueError('Unresolved evidence identifier')
        for rel in self.compatibility+self.relations:
            if rel.target_sku==self.sku:raise ValueError('Self relation is not allowed')
        if not self.synthetic and any(e.source_type=='synthetic' for e in self.evidence):
            raise ValueError('Synthetic evidence cannot support real product')
        return self


class Manifest(StrictRecord):
    schema_version: Literal['1.0']
    manifest_id: str=Field(min_length=1,max_length=128)
    created_at: datetime
    products: list[ProductEnrichment]=Field(min_length=1,max_length=10000)
    @model_validator(mode='after')
    def identifiers(self):
        if self.created_at.tzinfo is None:raise ValueError('Manifest timestamp needs timezone')
        skus=[p.sku for p in self.products]
        if len(set(skus))!=len(skus):raise ValueError('Duplicate SKU rows')
        return self


def assert_importable(manifest):
    for product in manifest.products:
        if product.synthetic:raise ValueError('Synthetic rows are never importable')
        if product.review.status!='approved':raise ValueError('Unreviewed product rows are rejected')
        if any(r.review.status!='approved' for r in product.relations+product.compatibility):
            raise ValueError('Unreviewed relation rows are rejected')


def dry_run_plan(manifest,catalog):
    """catalog is current SKU->attributes data. Pure planning only, no writes."""
    assert_importable(manifest)
    known=set(catalog);plan=[]
    for row in manifest.products:
        if row.sku not in known:raise ValueError('Unknown source SKU')
        for relation in row.relations+row.compatibility:
            if relation.target_sku not in known:raise ValueError('Unknown target SKU')
        existing=catalog[row.sku]
        import json
        patch={'enrichment_v1':json.dumps(row.model_dump(mode='json'),ensure_ascii=False)}
        for key in ('material','style','use'):
            claim=getattr(row,key)
            if claim:
                if key in existing and existing[key]!=claim.value:raise ValueError('Existing attribute conflict requires explicit review')
                if len(claim.value)>64:raise ValueError('Display attribute exceeds64char gate boundary')
                patch[key]=claim.value
        # On candidate B, complement_for_skus contains anchor A.
        # Relations are directional; no inferred inverse or automatic transitivity.
        anchors=[r.target_sku for r in row.relations if r.kind=='complement']
        if anchors:
            import json
            old=existing.get('complement_for_skus','[]')
            if not isinstance(old,str):raise ValueError('Existing complement evidence format conflicts')
            try:previous=json.loads(old)
            except (ValueError,TypeError):raise ValueError('Existing complement evidence is invalid')
            if not isinstance(previous,list) or not all(isinstance(s,str) for s in previous):
                raise ValueError('Existing complement evidence is invalid')
            combined=sorted(set(previous+anchors))
            if len(combined)>100:raise ValueError('Complement relation gate limit exceeded')
            patch['complement_for_skus']=json.dumps(combined)
        if 'enrichment_v1' in existing and existing['enrichment_v1']!=patch['enrichment_v1']:
            raise ValueError('Existing enrichment conflict requires explicit revision review')
        plan.append({'sku':row.sku,'operation':'would_merge_attributes','attribute_keys':sorted(patch),
                     'proposed_attributes':patch})
    return {'mode':'dry_run_only','writes':0,'products':plan}
