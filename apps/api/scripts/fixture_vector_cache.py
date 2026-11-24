"""Local document-vector cache. Integrity binding, never pickle or remote code."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tempfile
import time


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def model_fingerprint(path):
    # Resolve bytes, not just the caller-supplied revision. Include config,
    # tokenizer, pooling, normalization and all safetensors shards. No .py.
    names=sorted(p for p in Path(path).rglob('*') if p.is_file() and p.suffix in {'.json','.txt','.safetensors','.model','.tiktoken'})
    if not any(p.suffix=='.safetensors' for p in names):raise ValueError('Cache requires safetensors model weights')
    return hashlib.sha256(canonical([(str(p.relative_to(path)),file_sha(p)) for p in names])).hexdigest()


def binding(path,revision,sha,products,texts,document_prompt,threads):
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):raise ValueError('Cache requires exact model revision')
    return {'version':1,'model_revision':revision,'model_bytes_sha256':model_fingerprint(path),
        'catalog_sha256':sha,'ordered_skus':[p['sku'] for p in products],
        'document_texts_sha256':hashlib.sha256(canonical(texts)).hexdigest(),
        'document_prompt':document_prompt,'threads':threads,'dtype':'float32','device':'cpu',
        'attention':'eager','max_seq_length':256,'batch_size':1,'normalize_embeddings':True,
        'packages':{name:importlib.metadata.version(name) for name in ('torch','transformers','sentence-transformers','numpy')}}


def validate(vectors,count,dimension=None):
    import numpy as np
    if vectors.dtype!=np.float32 or vectors.ndim!=2 or vectors.shape[0]!=count or vectors.shape[1]<=0:
        raise ValueError('Invalid cached vector dtype/shape')
    if dimension is not None and vectors.shape[1]!=dimension:raise ValueError('Cached vector dimension mismatch')
    norms=np.linalg.norm(vectors,axis=1)
    if not np.isfinite(vectors).all() or not np.allclose(norms,1,atol=1e-4):raise ValueError('Invalid/nonunit cached vectors')


def location(root,contract):
    return Path(root)/hashlib.sha256(canonical(contract)).hexdigest()


def read(root,contract):
    import numpy as np
    directory=location(root,contract)
    if not directory.exists():return None
    metadata=json.loads((directory/'manifest.json').read_text())
    if metadata['binding']!=contract or file_sha(directory/'vectors.npy')!=metadata['vectors_sha256']:
        raise ValueError('Vector cache integrity/binding mismatch; no automatic overwrite')
    vectors=np.load(directory/'vectors.npy',allow_pickle=False)
    validate(vectors,len(contract['ordered_skus']),metadata['dimension'])
    return vectors,metadata


def write(root,contract,vectors,encode_ms):
    import numpy as np
    validate(vectors,len(contract['ordered_skus']))
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    destination=location(root,contract)
    if destination.exists():raise ValueError('Cache already exists; no overwrite')
    temporary=Path(tempfile.mkdtemp(prefix='.partial-',dir=root))
    np.save(temporary/'vectors.npy',vectors,allow_pickle=False)
    metadata={'binding':contract,'vectors_sha256':file_sha(temporary/'vectors.npy'),
        'dimension':int(vectors.shape[1]),'original_corpus_encode_ms':encode_ms,'created_unix':time.time()}
    (temporary/'manifest.json').write_bytes(canonical(metadata))
    # Rename of a completed nonempty directory avoids partially visible cache.
    # Concurrent writers fail rather than replace another complete result.
    temporary.rename(destination)
    return metadata


def pilot_indices(products,count):
    if not 20<=count<=50 or count>len(products):raise ValueError('Pilot must contain20..50 available documents')
    groups={}
    for i,p in enumerate(products):groups.setdefault(p['category'],[]).append(i)
    selected=[]
    for offset in range(max(map(len,groups.values()))):
        for category in sorted(groups):
            indices=groups[category]
            # Spread within every category instead of selecting contiguous variants.
            slots=max(1,(count+len(groups)-1)//len(groups))
            position=round(offset*(len(indices)-1)/max(1,slots-1)) if offset<slots else offset
            if position<len(indices) and indices[position] not in selected:selected.append(indices[position])
            if len(selected)==count:return selected
    raise ValueError('Not enough distinct pilot documents')
