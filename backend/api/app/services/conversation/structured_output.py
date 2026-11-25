"""Explicit stage schemas for supported nonstreaming Groq models.

Provider contract: https://console.groq.com/docs/structured-outputs
Runtime validation remains authoritative for domain constraints.
"""
import copy
import logging

logger = logging.getLogger('airdeliver.structured_output')
STRICT_MODELS = frozenset({
    'openai/gpt-oss-20b', 'openai/gpt-oss-120b',
    'qwen/qwen3.8-27b', 'meta-models/muse-spark-open',
})


class StructuredOutputError(ValueError):
    """Transport succeeded but the returned JSON object was invalid."""


def strict_schema(model):
    """Do not weaken required domain fields or invent nullable alternatives."""
    schema = copy.deepcopy(model.model_json_schema())

    def visit(node):
        if isinstance(node, dict):
            node.pop('default', None)
            node.pop('title', None)  # Annotation only, never a validation/field description.
            if node.get('type') == 'object':
                if node.get('additionalProperties') not in (None, False):
                    raise ValueError('Open dictionary cannot be provider constrained')
                node['additionalProperties'] = False
                node['required'] = list(node.get('properties', {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


def response_format(model_id, model):
    if model_id not in STRICT_MODELS:
        logger.warning(
            'structured_output.mode mode=json_object cause=unsupported_model schema=%s',
            model.__name__,
        )
        return {'type': 'json_object'}
    return {'type': 'json_schema', 'json_schema': {
        'name': model.__name__, 'strict': True, 'schema': strict_schema(model),
    }}


async def infer_schema(infer, messages, model):
    owner = getattr(infer, '__self__', None)
    scoped = getattr(owner, '_execute_schema_inference', None)
    if callable(scoped):
        raw = await scoped(messages, model)
    else:
        # Injected/legacy adapters are not silently advertised constrained.
        logger.debug('structured_output.mode mode=injected_adapter schema=%s', model.__name__)
        raw = await infer(messages)
    # Even provider-constrained output is untrusted until runtime validation.
    # Keep raw text for each stage's schema diagnostics, but reject duplicate
    # keys/nonfinite values before any schema parser can silently pick one.
    from app.services.strict_planner_json import planner_object
    try:
        planner_object(raw)
    except ValueError as exc:
        raise StructuredOutputError('Invalid structured JSON object') from exc
    return raw
