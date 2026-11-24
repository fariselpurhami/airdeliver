"""Versioned retrieval spaces. Default remains GTE until explicit owner activation.

A profile selects model/revision/dimension AND every text-vector namespace.
Never insert vectors from different models into the same collection.
"""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class RetrievalSpace:
    key:str
    model:str
    revision:str
    dimension:int
    collection:str
    search_index:str
    intent_collection:str
    memory_collection:str
    query_prompt:str=''

SPACES={
    'granite-v1':RetrievalSpace('granite-v1','ibm-granite/granite-embedding-311m-multilingual-r2',
        '44399559930365213510b1ee2eb15ded83374f0e',768,'airdeliver_products_granite_v1',
        'airdeliver_products_granite_v1','airdeliver_intents_granite_v1','airdeliver_memory_granite_v1'),
    'gte-v1':RetrievalSpace('gte-v1','Alibaba-NLP/gte-Qwen2-1.5B-instruct',
        'a9af15a6372d7d6b25e9fb07c2ccb9e1fe645644',1536,'airdeliver_products_sota_v4',
        'airdeliver_products','airdeliver_intents_sota_v4','airdeliver_memory_sota_v4'),
    'harrier-v1':RetrievalSpace('harrier-v1','microsoft/harrier-oss-v1-0.6b',
        'f9b9dc8d367d443f2479d27aa5d8d2850c0774ee',1024,'airdeliver_products_harrier_v1',
        'airdeliver_products_harrier_v1','airdeliver_intents_harrier_v1','airdeliver_memory_harrier_v1',
        'Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: '),
}

def retrieval_space(key=None):
    key=key or os.environ.get('PRODUCT_TEXT_PROFILE','gte-v1')
    if key not in SPACES:raise ValueError('Unknown PRODUCT_TEXT_PROFILE; no fallback')
    return SPACES[key]

ACTIVE_SPACE=retrieval_space()
PRODUCT_TEXT_MODEL_NAME=ACTIVE_SPACE.model
PRODUCT_TEXT_MODEL_DIMENSION=ACTIVE_SPACE.dimension
PRODUCT_TEXT_COLLECTION=ACTIVE_SPACE.collection
DEFAULT_PRODUCT_TEXT_MODEL_REVISION=ACTIVE_SPACE.revision
PRODUCT_SEARCH_INDEX=ACTIVE_SPACE.search_index
PRODUCT_INTENT_COLLECTION=ACTIVE_SPACE.intent_collection
PRODUCT_MEMORY_COLLECTION=ACTIVE_SPACE.memory_collection
PRODUCT_QUERY_PROMPT=ACTIVE_SPACE.query_prompt

PRODUCT_TEXT_PROFILE=ACTIVE_SPACE.key
