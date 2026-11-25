"""Pure integrity/cache tests. No downloaded model or owner machine execution."""
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture_vector_cache',ROOT/'scripts/fixture_vector_cache.py');cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)


def contract(tmp_path):
    model=tmp_path/'model';model.mkdir();(model/'model.safetensors').write_bytes(b'local-test-bytes');(model/'config.json').write_text('{}')
    return model,cache.binding(model,'a'*40,'b'*64,[{'sku':'a'},{'sku':'b'}],['one','two'],'',2)


def test_write_read_integrity_and_no_overwrite(tmp_path):
    _,binding=contract(tmp_path);vectors=np.array([[1.,0.],[0.,1.]],dtype=np.float32);root=tmp_path/'cache'
    assert cache.read(root,binding) is None
    cache.write(root,binding,vectors,1234.)
    saved,metadata=cache.read(root,binding)
    assert np.array_equal(saved,vectors) and metadata['original_corpus_encode_ms']==1234.
    with pytest.raises(ValueError):cache.write(root,binding,vectors,0)
    file=cache.location(root,binding)/'vectors.npy';file.write_bytes(file.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='integrity'):cache.read(root,binding)


@pytest.mark.parametrize('field,value',[('model_revision','c'*40),('document_prompt','passage'),('threads',1),('catalog_sha256','d'*64),('document_texts_sha256','f'*64),('ordered_skus',['b','a']),('dtype','float16'),('attention','sdpa')])
def test_different_binding_never_reuses(tmp_path,field,value):
    _,binding=contract(tmp_path);root=tmp_path/'cache';cache.write(root,binding,np.eye(2,dtype=np.float32),1)
    assert cache.read(root,{**binding,field:value}) is None


def test_actual_model_bytes_change_key_even_with_same_claimed_revision(tmp_path):
    model,binding=contract(tmp_path);(model/'config.json').write_text('{"changed":true}')
    other=cache.binding(model,'a'*40,'b'*64,[{'sku':'a'},{'sku':'b'}],['one','two'],'',2)
    assert other['model_bytes_sha256']!=binding['model_bytes_sha256']


@pytest.mark.parametrize('vectors',[np.ones((2,2)),np.zeros((2,2),dtype=np.float32),np.ones((1,2),dtype=np.float32),np.array([[float('nan'),0],[0,1]],dtype=np.float32)])
def test_invalid_vectors_fail(vectors):
    with pytest.raises(ValueError):cache.validate(vectors,2)


def test_pilot_is_category_spread_deterministic_and_bounded():
    products=[{'category':str(i//100)} for i in range(1000)]
    ids=cache.pilot_indices(products,20)
    assert len(set(ids))==20 and len({products[i]['category'] for i in ids})==10
    assert ids==cache.pilot_indices(products,20)
    for count in (19,51):
        with pytest.raises(ValueError):cache.pilot_indices(products,count)


def test_metadata_tamper_and_safe_numpy_no_pickle(tmp_path):
    _,binding=contract(tmp_path);root=tmp_path/'cache';cache.write(root,binding,np.eye(2,dtype=np.float32),1)
    file=cache.location(root,binding)/'manifest.json';metadata=json.loads(file.read_text());metadata['binding']['threads']=999;file.write_text(json.dumps(metadata))
    with pytest.raises(ValueError):cache.read(root,binding)
