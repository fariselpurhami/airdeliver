"""Offline retrieval A/B, not a production prompt switch or quality certification.

Input JSON: documents [{id: str, text: str}], queries
[{id: str, text: str, relevant_ids: [str]}]. Labels must be human-reviewed.
No network/provider/database writes. Requires the pinned GTE weights in cache.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.catalog_contract import (
    PRODUCT_TEXT_MODEL_NAME, PRODUCT_TEXT_MODEL_DIMENSION,
    DEFAULT_PRODUCT_TEXT_MODEL_REVISION,
)

MODEL_CARD = 'https://huggingface.co/Alibaba-NLP/gte-Qwen2-1.5B-instruct/raw/a9af15a6372d7d6b25e9fb07c2ccb9e1fe645644/README.md'


def validate_fixture(data):
    if not isinstance(data, dict):
        raise ValueError('Fixture must be an object')
    for section in ('documents', 'queries'):
        rows = data.get(section)
        if not isinstance(rows, list) or not rows:
            raise ValueError('Fixture requires nonempty documents and queries')
        seen = set()
        for row in rows:
            if (not isinstance(row, dict) or not isinstance(row.get('id'), str)
                    or not row['id'].strip() or row['id'] in seen
                    or not isinstance(row.get('text'), str) or not row['text'].strip()):
                raise ValueError('Fixture IDs must be unique strings and text nonempty')
            seen.add(row['id'])
    ids = {row['id'] for row in data['documents']}
    for query in data['queries']:
        relevant = query.get('relevant_ids')
        if (not isinstance(relevant, list) or not relevant
                or any(not isinstance(x, str) or x not in ids for x in relevant)
                or len(set(relevant)) != len(relevant)):
            raise ValueError('Each query needs unique relevant document IDs in the fixture')
    return data


def metrics(ranked, relevant, k):
    relevant = set(relevant)
    hits = [index for index, identity in enumerate(ranked[:k], 1) if identity in relevant]
    ideal = sum(1 / math.log2(i + 1) for i in range(1, min(k, len(relevant)) + 1))
    return {'recall_at_k': len(hits) / len(relevant),
            'mrr_at_k': 1 / hits[0] if hits else 0.0,
            'ndcg_at_k': sum(1 / math.log2(i + 1) for i in hits) / ideal}


def evaluate(model, fixture, *, k=5, dimension=PRODUCT_TEXT_MODEL_DIMENSION, clock=time.perf_counter):
    import numpy as np
    fixture = validate_fixture(fixture)
    if type(k) is not int or k < 1:
        raise ValueError('k must be positive')
    if not isinstance(getattr(model, 'prompts', None), dict) or not model.prompts.get('query'):
        raise ValueError('Pinned model has no query prompt; refusing an invented substitute')

    def checked(vector, shape):
        result = np.asarray(vector, dtype=float)
        if result.shape != shape or not np.isfinite(result).all():
            raise ValueError('Invalid embedding shape or nonfinite values')
        norms = np.linalg.norm(result, axis=-1, keepdims=True)
        if np.any(norms <= 0):
            raise ValueError('Zero embedding vector')
        return result / norms

    documents = fixture['documents']
    started = clock()
    # Explicit empty prompt prevents any configured default query prompt on documents.
    vectors = checked(model.encode([d['text'] for d in documents], prompt='',
                                   convert_to_numpy=True, normalize_embeddings=True),
                      (len(documents), dimension))
    document_seconds = clock() - started
    results = {'raw': [], 'query_prompt': []}
    # Alternate order across queries to reduce systematic first-mode warmup bias.
    # This remains a small paired benchmark, not a production latency SLA.
    for index, query in enumerate(fixture['queries']):
        order = ('raw', 'query_prompt') if index % 2 == 0 else ('query_prompt', 'raw')
        for mode in order:
            started = clock()
            options = {'prompt': ''} if mode == 'raw' else {'prompt_name': 'query'}
            vector = checked(model.encode(query['text'], convert_to_numpy=True,
                                           normalize_embeddings=True, **options), (dimension,))
            elapsed = clock() - started
            scores = vectors @ vector
            ranked = [documents[i]['id'] for i in np.argsort(-scores, kind='stable')]
            results[mode].append({'query_id': query['id'], 'top_ids': ranked[:k],
                                  'seconds': round(elapsed, 6),
                                  **metrics(ranked, query['relevant_ids'], k)})
    summary = {}
    for mode, rows in results.items():
        summary[mode] = {name: sum(r[name] for r in rows) / len(rows)
                         for name in ('recall_at_k', 'mrr_at_k', 'ndcg_at_k')}
        summary[mode]['latency_seconds_p50'] = float(np.percentile([r['seconds'] for r in rows], 50))
        summary[mode]['latency_seconds_p95'] = float(np.percentile([r['seconds'] for r in rows], 95))
    return {'schema_version': 1, 'model': PRODUCT_TEXT_MODEL_NAME,
            'revision': DEFAULT_PRODUCT_TEXT_MODEL_REVISION, 'dimension': dimension,
            'fixture_sha256': hashlib.sha256(json.dumps(fixture, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'query_prompt_sha256': hashlib.sha256(model.prompts['query'].encode()).hexdigest(),
            'documents': len(documents), 'queries': len(fixture['queries']), 'k': k,
            'document_seconds': round(document_seconds, 6), 'summary': summary, 'results': results,
            'source': MODEL_CARD,
            'scope': 'Offline labeled-fixture comparison only. No production switch, hybrid search, compatibility guarantee or provider evaluation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    fixture = validate_fixture(json.loads(Path(args.fixture).read_text()))
    # Offline is mandatory: even a cache miss must not silently download weights/code.
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(PRODUCT_TEXT_MODEL_NAME,
                                revision=DEFAULT_PRODUCT_TEXT_MODEL_REVISION,
                                local_files_only=True, trust_remote_code=False, device=args.device)
    result = evaluate(model, fixture, k=args.k)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps({'scope': result['scope'], 'summary': result['summary']}))


if __name__ == '__main__':
    main()
