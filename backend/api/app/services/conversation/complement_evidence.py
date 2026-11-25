"""Conservative catalog-asserted relation gate, not a semantic ranker.

The importing catalog owner must review relation data. Attributes are not proof
of physical compatibility. Text similarity/name tokens cannot create relations.
"""
import json
from typing import Any


def catalog_asserts_complement(anchor: Any, candidate: Any) -> bool:
    if anchor is None or candidate is None or getattr(anchor, 'id', None) == getattr(candidate, 'id', None):
        return False
    anchor_sku = getattr(anchor, 'sku', None)
    attributes = getattr(candidate, 'attributes', None)
    if not isinstance(anchor_sku, str) or not anchor_sku or not isinstance(attributes, dict):
        return False
    raw = attributes.get('complement_for_skus')
    if not isinstance(raw, str) or len(raw) > 16384:
        return False
    try:
        skus = json.loads(raw)
    except (ValueError, TypeError):
        return False
    if (not isinstance(skus, list) or not skus or len(skus) > 100
            or any(not isinstance(sku, str) or not sku or len(sku) > 128 for sku in skus)):
        return False
    return anchor_sku in skus
