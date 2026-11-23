import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas.sku_enrichment import Manifest,assert_importable,dry_run_plan
from scripts.plan_sku_enrichment import load_manifest,MAX_BYTES

EXAMPLE=Path(__file__).resolve().parents[3]/'docs/catalog/sku-enrichment.synthetic.json'


def real():
    row=json.loads(EXAMPLE.read_text());p=row['products'][0];p['synthetic']=False
    p['evidence'][0]['source_type']='manufacturer'
    review={'status':'approved','reviewer':'Fixture reviewer','reviewed_at':'2026-11-23T11:00:00+02:00','notes':'Fixture only'}
    p['review']=review
    for r in p['relations']+p['compatibility']:r['review']=review
    return row


def test_synthetic_is_valid_shape_but_never_importable():
    manifest,_=load_manifest(EXAMPLE)
    with pytest.raises(ValueError,match='Synthetic'):assert_importable(manifest)


@pytest.mark.parametrize('change',[
    lambda d:d['products'][0].update(review={'status':'draft','notes':'not reviewed'}),
    lambda d:d['products'][0]['relations'][0].update(review={'status':'rejected','notes':'rejected'}),
])
def test_unreviewed_product_or_relation_rejected(change):
    d=real();change(d);m=Manifest.model_validate_json(json.dumps(d))
    with pytest.raises(ValueError):assert_importable(m)


@pytest.mark.parametrize('change',[
    lambda d:d['products'][0]['material'].update(evidence_ids=['missing']),
    lambda d:d['products'][0].update(unknown_property='bad'),
    lambda d:d['products'][0]['rating'].update(count=0),
    lambda d:d['products'][0]['rating'].update(value='NaN'),
    lambda d:d['products'][0]['relations'][0].update(target_sku=d['products'][0]['sku']),
    lambda d:d['products'].append(copy.deepcopy(d['products'][0])),
    lambda d:d['products'][0]['evidence'][0].update(captured_at='2026-11-23T11:00:00'),
    lambda d:d['products'][0]['evidence'][0].update(source_type='synthetic'),
])
def test_schema_rejects_invalid_evidence_types_refs_and_duplicates(change):
    d=real();change(d)
    with pytest.raises((ValidationError,ValueError)):Manifest.model_validate_json(json.dumps(d))


def test_dry_run_preserves_existing_attributes_and_relation_direction():
    m=Manifest.model_validate_json(json.dumps(real()));p=m.products[0]
    catalog={p.sku:{'untouched':'yes','complement_for_skus':'["OLD"]'}}
    catalog.update({r.target_sku:{} for r in p.relations+p.compatibility});before=copy.deepcopy(catalog)
    plan=dry_run_plan(m,catalog)
    assert plan['writes']==0 and catalog==before
    patch=plan['products'][0]['proposed_attributes']
    assert set(json.loads(patch['complement_for_skus']))=={'OLD','SYNTHETIC-ANCHOR-C'}
    assert 'SYNTHETIC-ALT-D' not in patch['complement_for_skus']
    assert patch['material']=='canvas' and isinstance(patch['enrichment_v1'],str)


def test_catalog_missing_sku_or_conflicting_attribute_rejected():
    m=Manifest.model_validate_json(json.dumps(real()));p=m.products[0]
    with pytest.raises(ValueError):dry_run_plan(m,{})
    catalog={p.sku:{'material':'leather'}}
    catalog.update({r.target_sku:{} for r in p.relations+p.compatibility})
    with pytest.raises(ValueError,match='conflict'):dry_run_plan(m,catalog)


def test_duplicate_json_keys_and_oversize_files_rejected(tmp_path):
    p=tmp_path/'input.json';p.write_text('{"schema_version":"1.0","schema_version":"1.0"}')
    with pytest.raises(ValueError,match='Duplicate'):load_manifest(p)
    p.write_bytes(b' '* (MAX_BYTES+1))
    with pytest.raises(ValueError,match='8MiB'):load_manifest(p)
