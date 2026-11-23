import copy
import math
import numpy as np
import pytest
from scripts.evaluate_gte_query_prompt import evaluate, metrics, validate_fixture


FIXTURE = {'documents': [{'id': 'a', 'text': 'shoe'}, {'id': 'b', 'text': 'phone'}],
           'queries': [{'id': 'en', 'text': 'running', 'relevant_ids': ['a']},
                       {'id': 'ar', 'text': 'تليفون', 'relevant_ids': ['b']}]}


class Encoder:
    prompts = {'query': 'Pinned query prompt'}

    def __init__(self):
        self.calls = []

    def encode(self, value, **options):
        self.calls.append((value, options))
        if isinstance(value, list):
            return np.eye(2)
        if options.get('prompt_name') == 'query':
            return [1, 0] if value == 'running' else [0, 1]
        return [0, 1] if value == 'running' else [1, 0]


def test_paired_eval_reuses_documents_and_compares_query_only():
    model = Encoder()
    result = evaluate(model, FIXTURE, k=1, dimension=2)
    assert len(model.calls) == 5
    assert model.calls[0][1]['prompt'] == ''
    assert [c[1].get('prompt_name', 'raw') for c in model.calls[1:]] == ['raw', 'query', 'query', 'raw']
    assert result['summary']['raw']['recall_at_k'] == 0
    assert result['summary']['query_prompt']['recall_at_k'] == 1
    assert result['fixture_sha256'] == evaluate(Encoder(), FIXTURE, dimension=2)['fixture_sha256']
    assert 'running' not in str(result) and 'تليفون' not in str(result)


def test_rank_metrics_account_for_multiple_relevant_documents():
    result = metrics(['x', 'b', 'a'], ['a', 'b'], 2)
    assert result['recall_at_k'] == .5
    assert result['mrr_at_k'] == .5
    assert result['ndcg_at_k'] == pytest.approx((1 / math.log2(3)) / (1 + 1 / math.log2(3)))


@pytest.mark.parametrize('change', ['duplicate', 'unknown', 'empty', 'repeated_label'])
def test_invalid_fixture_rejected_before_encoding(change):
    fixture = copy.deepcopy(FIXTURE)
    if change == 'duplicate': fixture['documents'][1]['id'] = 'a'
    if change == 'unknown': fixture['queries'][0]['relevant_ids'] = ['missing']
    if change == 'empty': fixture['queries'][0]['text'] = ''
    if change == 'repeated_label': fixture['queries'][0]['relevant_ids'] = ['a', 'a']
    with pytest.raises(ValueError): validate_fixture(fixture)


@pytest.mark.parametrize('bad', [[0, 0], [float('nan'), 1], [1, 2, 3]])
def test_bad_embedding_rejected(bad):
    model = Encoder()
    original = model.encode
    model.encode = lambda value, **kw: original(value, **kw) if isinstance(value, list) else bad
    with pytest.raises(ValueError): evaluate(model, FIXTURE, dimension=2)


def test_missing_model_prompt_rejected():
    model = Encoder(); model.prompts = {}
    with pytest.raises(ValueError): evaluate(model, FIXTURE, dimension=2)
