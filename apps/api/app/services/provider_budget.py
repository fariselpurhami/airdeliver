"""Bounded Groq admission and safe diagnostics. No prompt/body logging.

The UTF-8 byte count is a conservative token upper bound, not a tokenizer
measurement. It needs no downloaded tokenizer and cannot undercount multilingual
text for byte-fallback tokenizers. Provider framing allowance is additional.
State is process-local, not an organization-wide or cross-worker quota ledger.
"""
import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import math
import re
import weakref
from groq import APIStatusError, APIConnectionError

logger = logging.getLogger('airdeliver.provider_budget')

class ProviderCooldownError(RuntimeError):
    status_code = 429

class ProviderInputBudgetError(ValueError):
    pass

def token_upper_bound(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 128

def retry_delay(exc, attempt, default_minimum=.5):
    headers = getattr(getattr(exc, 'response', None), 'headers', {})
    for key, divisor in [('retry-after', 1), ('retry-after-ms', 1000)]:
        raw = headers.get(key)
        if raw is None:
            continue
        try:
            delay = float(raw) / divisor
        except (ValueError, TypeError):
            try:
                delay = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                continue
        if math.isfinite(delay) and delay >= 0:
            return delay
    return max(default_minimum, min(4.0, .5 * 2 ** attempt))

def quota_metadata(exc):
    """Only bounded numeric/duration values, never raw messages or headers."""
    headers = getattr(getattr(exc, 'response', None), 'headers', {})
    result = {}
    for key in ('x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests',
                'x-ratelimit-limit-tokens', 'x-ratelimit-remaining-tokens'):
        value = headers.get(key, '')
        if re.fullmatch(r'\d{1,12}', str(value)):
            result[key.removeprefix('x-ratelimit-').replace('-', '_')] = int(value)
    for key in ('retry-after', 'x-ratelimit-reset-requests', 'x-ratelimit-reset-tokens'):
        value = str(headers.get(key, ''))
        if re.fullmatch(r'[0-9.hms]{1,32}', value):
            result[key.removeprefix('x-ratelimit-').replace('-', '_')] = value
    # Classify only an allowlisted unit; do not retain the provider message.
    body = getattr(exc, 'body', None)
    error = body.get('error', body) if isinstance(body, dict) else {}
    text = error.get('message', '') if isinstance(error, dict) else ''
    for unit in ('TPM', 'TPD', 'RPM', 'RPD', 'ITPM', 'OTPM'):
        if isinstance(text, str) and re.search(r'\(' + unit + r'\)', text):
            result['quota_unit'] = unit
            break
    return result

class Admission:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.until = 0.0

_states = weakref.WeakKeyDictionary()

def admission(model):
    loop = asyncio.get_running_loop()
    return _states.setdefault(loop, {}).setdefault(model, Admission())

def log_usage(response,model,stage,messages,output):
    usage=getattr(response,'usage',None)
    values={k:getattr(usage,k,None) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    values={k:v for k,v in values.items() if type(v) is int and v>=0}
    logger.info('provider.usage model=%s stage=%s input_bytes_upper=%d output_cap=%d usage=%s',model,stage,token_upper_bound(messages),output,values)

async def complete(create, *, model, messages, response_format, timeout, stage='inference'):
    output = {'SpecDraft': 1200, 'SourceReview': 1200,'GroundingReview':256,'ShoppingDraft':640,'RouterDecision':768}.get(stage, 2048)
    estimate = token_upper_bound({'messages': messages, 'response_format': response_format})
    if stage in {'SpecDraft', 'SourceReview'} and estimate + output > 7800:
        logger.warning('provider.input_withheld stage=%s input_token_upper=%d output_cap=%d', stage, estimate, output)
        raise ProviderInputBudgetError('Input exceeds conservative local token budget')
    state = admission(model)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    async with asyncio.timeout(timeout):
        async with state.lock:
            for attempt in range(3):
                remaining = state.until - loop.time()
                while remaining > 0:
                    if remaining >= deadline - loop.time():
                        raise ProviderCooldownError('Provider cooldown exceeds caller deadline')
                    await asyncio.sleep(max(.001, remaining))
                    remaining = state.until - loop.time()
                try:
                    from app.services.shared_provider_admission import shared_provider_slot
                    async with shared_provider_slot(model,messages,response_format,output,max(.001,deadline-loop.time())) as reservation:
                        try:
                            from app.services.provider_response_observation import observed_create
                            response=await observed_create(create,reservation,model=model, messages=messages, temperature=0.0,
                                                response_format=response_format, max_tokens=output,
                                                **({'reasoning_effort':'low'} if model in {'openai/gpt-oss-120b','openai/gpt-oss-20b'} and stage in {'RouterDecision','ShoppingDraft','GroundingReview'} else {}))
                            reservation.observe(response)
                        except APIStatusError as failure:
                            if failure.status_code==429:await reservation.quota(retry_delay(failure,attempt,60.0))
                            raise
                    log_usage(response,model,stage,messages,output)
                    return response
                except Exception as exc:
                    status = getattr(exc, 'status_code', None)
                    transient = isinstance(exc, (APIConnectionError, TimeoutError)) or (
                        isinstance(exc, APIStatusError) and (status in (408, 409, 429) or status >= 500))
                    if not transient:
                        raise
                    delay = retry_delay(exc, attempt, 60.0 if status == 429 else .5)
                    if status == 429:
                        state.until = max(state.until, loop.time() + delay)
                        logger.warning('provider.quota stage=%s input_token_upper=%d output_cap=%d metadata=%s',
                                       stage, estimate, output, quota_metadata(exc))
                    if attempt == 2 or delay >= deadline - loop.time():
                        raise
                    if status != 429:
                        await asyncio.sleep(delay)
