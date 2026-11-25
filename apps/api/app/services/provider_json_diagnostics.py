"""Structural categories only from provider failed JSON. Never retain model text."""
import json

def failed_json_diagnostics(exc, wire_format, output_cap):
    body = getattr(exc, 'body', None)
    error = body.get('error', body) if isinstance(body, dict) else {}
    if not isinstance(error, dict):
        return {'generation': 'absent'}
    raw = error.get('failed_generation')
    result = {'generation': 'present' if isinstance(raw, str) else 'absent'}
    finish = error.get('finish_reason')
    if isinstance(finish, str) and finish in {'length', 'stop', 'content_filter'}:
        result['finish'] = finish
    usage = error.get('usage', body.get('usage') if isinstance(body, dict) else None)
    if isinstance(usage, dict):
        completion = usage.get('completion_tokens')
        if type(completion) is int and completion >= 0:
            result['completion_tokens'] = min(completion, 1000000)
            result['output_cap_reached'] = completion >= output_cap
    if not isinstance(raw, str):
        return result
    result['characters'] = min(len(raw), 100001)
    if len(raw) > 100000:
        result['json'] = 'oversize'
        return result
    duplicates = False

    def pairs(values):
        nonlocal duplicates
        out = {}
        for (key, value) in values:
            if key in out:
                duplicates = True
            out[key] = value
        return out

    def reject_constant(value):
        raise ValueError('Non-JSON numeric constant')
    try:
        parsed = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    except json.JSONDecodeError as failure:
        result['json'] = 'invalid'
        result['parse_position'] = failure.pos
        result['parse_near_end'] = failure.pos >= max(0, len(raw) - 8)
        return result
    except (RecursionError, ValueError):
        result['json'] = 'invalid_or_complex'
        return result
    result['json'] = 'valid'
    result['duplicate_keys'] = duplicates
    schema = wire_format.get('json_schema', {}).get('schema') if isinstance(wire_format, dict) else None
    if not isinstance(schema, dict):
        result['schema'] = 'not_supplied'
        return result
    categories = set()
    nodes = 0

    def check(value, node, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > 3000 or depth > 20:
            categories.add('complexity_limit')
            return
        if '$ref' in node:
            ref = node['$ref']
            if isinstance(ref, str) and ref.startswith('#/$defs/'):
                node = schema.get('$defs', {}).get(ref.split('/')[-1], {})
        expected = node.get('type')
        valid = {'object': isinstance(value, dict), 'array': isinstance(value, list), 'string': isinstance(value, str), 'integer': type(value) is int, 'number': type(value) in (int, float), 'boolean': type(value) is bool, 'null': value is None}
        if expected in valid and (not valid[expected]):
            categories.add('value_type')
            return
        if isinstance(value, dict):
            props = node.get('properties', {})
            if set(node.get('required', ())) - value.keys():
                categories.add('missing_required')
            if node.get('additionalProperties') is False and value.keys() - props.keys():
                categories.add('unexpected_field')
            for (key, item) in value.items():
                if nodes > 3000:
                    categories.add('complexity_limit')
                    break
                if key in props:
                    check(item, props[key], depth + 1)
        if isinstance(value, list):
            if len(value) > node.get('maxItems', 100000):
                categories.add('array_too_long')
            if len(value) < node.get('minItems', 0):
                categories.add('array_too_short')
            if len(value) > 100:
                categories.add('inspection_partial')
            for item in value[:100]:
                check(item, node.get('items', {}), depth + 1)
        if isinstance(value, str):
            if len(value) > node.get('maxLength', 1000000):
                categories.add('text_too_long')
            if len(value) < node.get('minLength', 0):
                categories.add('text_too_short')
        if 'enum' in node and value not in node['enum']:
            categories.add('enum_mismatch')
    check(parsed, schema)
    result['schema'] = 'violation' if categories else 'no_detected_violation'
    result['categories'] = sorted(categories)
    return result


def provider_error_shape(exc):
    """Bounded structure, never arbitrary keys, provider prose or failed output."""
    body=getattr(exc,'body',None)
    error=body.get('error',body) if isinstance(body,dict) else None
    allowed={'json_validate_failed','model_decommissioned','model_not_found',
             'rate_limit_exceeded','context_length_exceeded','invalid_request_error','invalid_api_key'}
    result={'body_type':type(body).__name__ if type(body) in (dict,list,str,type(None)) else 'other',
            'nested_error':isinstance(body,dict) and isinstance(body.get('error'),dict)}
    if isinstance(error,dict):
        result['has_code']=isinstance(error.get('code'),str)
        result['has_type']=isinstance(error.get('type'),str)
        result['has_generation']=isinstance(error.get('failed_generation'),str)
        for field in ('code','type'):
            if isinstance(error.get(field),str) and error[field] in allowed:result[field]=error[field]
    return result
