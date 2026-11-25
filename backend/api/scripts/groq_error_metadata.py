"""Fixed-vocabulary provider diagnostics. Never serialize error text or payloads."""
import re


def safe_error_metadata(exc):
    body = getattr(exc, 'body', None)
    fields = body if isinstance(body, dict) else {}
    if isinstance(fields.get('error'), dict):
        fields = fields['error']
    codes = {'model_not_found', 'model_decommissioned', 'invalid_api_key',
             'rate_limit_exceeded', 'insufficient_quota', 'permission_denied',
             'organization_restricted', 'not_found', 'json_validate_failed',
             'invalid_request_error', 'invalid_value', 'unsupported_parameter',
             'context_length_exceeded', 'generation_failed'}
    types = {'invalid_request_error', 'invalid_request', 'authentication_error',
             'permission_error', 'rate_limit_error', 'server_error', 'requests'}
    params = {'model', 'messages', 'temperature', 'top_p', 'max_tokens',
              'max_completion_tokens', 'response_format', 'reasoning_format',
              'reasoning_effort', 'include_reasoning', 'stop', 'stream', 'n',
              'tools', 'tool_choice', 'seed', 'user'}
    def allowed(value, vocabulary):
        return value if isinstance(value, str) and value in vocabulary else 'not_in_allowlist'
    status = getattr(exc, 'status_code', None)
    response = getattr(exc, 'response', None)
    headers = getattr(response, 'headers', {})
    content_type = headers.get('content-type', '').split(';', 1)[0].strip().lower()
    request_id = None
    for header in ('x-request-id', 'x-groq-request-id'):
        value = headers.get(header, '')
        if isinstance(value, str) and re.fullmatch(r'(?:req_|greq_)[A-Za-z0-9_-]{8,120}', value):
            request_id = value
            break
    # Groq1.7 does not expose OpenAI-style code/type/param attributes.
    return {'error_class': type(exc).__name__,
            'http_status': status if type(status) is int else None,
            'provider_code': allowed(getattr(exc, 'code', None) or fields.get('code'), codes),
            'provider_error_type': allowed(fields.get('type'), types),
            'provider_param': allowed(fields.get('param'), params),
            'response_content_type': content_type if content_type in {
                'application/json', 'text/html', 'text/plain', 'application/problem+json'
            } else 'unknown_or_missing',
            'request_id': request_id,
            'scope': 'sanitized response metadata only; not_in_allowlist is a local redaction label, not account policy'}
