"""Optional OpenRouter free-model client. Additive and inert: nothing imports it by default.

It exposes the same `chat.completions.create` surface the service already calls on the Groq SDK client,
so an evaluation harness (or a later flag-gated wiring) can inject it without touching Groq paths.
Hard safety properties, all offline-testable:
- only models whose id ends in ':free' are accepted (a paid route is refused before any request);
- a local daily request cap fails closed before the provider's own limit is reached;
- no retry on any status, a 429 is raised once as the Groq SDK's RateLimitError (existing cooldown code handles it);
- the API key is never logged and never part of an exception message.
Unverified until a first real call (needs the owner's written permission naming scope): whether the model honours
`response_format`, and how many tokens its reasoning uses. Both are configurable here, code validation stays authoritative.
"""
import time
from typing import Any, Dict, List, Optional

import httpx
from groq import APIStatusError, RateLimitError
from groq.types.chat import ChatCompletion

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_FREE_MODEL = 'nvidia/nemotron-3-ultra-550b-a55b:free'
FREE_DAILY_LIMIT = 50
DEFAULT_LOCAL_CAP = 40


class OpenRouterConfigError(ValueError):
    pass


class DailyCapReached(RuntimeError):
    pass


class _Completions:
    def __init__(self, owner: 'OpenRouterClient'):
        self._owner = owner

    async def create(self, **kwargs: Any) -> ChatCompletion:
        return await self._owner._create(**kwargs)


class _Chat:
    def __init__(self, owner: 'OpenRouterClient'):
        self.completions = _Completions(owner)


class OpenRouterClient:
    def __init__(self, *, api_key: str, http_client: Optional[httpx.AsyncClient] = None, base_url: str = OPENROUTER_BASE_URL,
                 daily_cap: int = DEFAULT_LOCAL_CAP, reasoning_effort: str = 'low', min_max_tokens: int = 1024,
                 json_mode: str = 'json_object', clock=time.time):
        if not isinstance(api_key, str) or not api_key.strip():
            raise OpenRouterConfigError('api_key_missing')
        if not base_url.startswith('https://'):
            raise OpenRouterConfigError('base_url_must_be_https')
        if not 1 <= daily_cap <= FREE_DAILY_LIMIT:
            raise OpenRouterConfigError('daily_cap_outside_free_limit')
        if json_mode not in ('json_object', 'json_schema', 'none'):
            raise OpenRouterConfigError('json_mode_invalid')
        self._key = api_key.strip()
        self._http = http_client or httpx.AsyncClient(timeout=30, trust_env=False)
        self._base = base_url.rstrip('/')
        self._cap = daily_cap
        self._effort = reasoning_effort
        self._min_tokens = min_max_tokens
        self._json_mode = json_mode
        self._clock = clock
        self._day = None
        self._used = 0
        self.chat = _Chat(self)

    @property
    def used_today(self) -> int:
        self._roll()
        return self._used

    def _roll(self) -> None:
        day = int(self._clock() // 86400)
        if day != self._day:
            self._day, self._used = day, 0

    def build_payload(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        model = kwargs.get('model')
        if not isinstance(model, str) or not model.endswith(':free'):
            raise OpenRouterConfigError('only_free_models_allowed')
        messages: List[Dict[str, Any]] = kwargs.get('messages') or []
        if not messages:
            raise OpenRouterConfigError('messages_required')
        payload: Dict[str, Any] = {'model': model, 'messages': messages,
                                   'max_tokens': max(int(kwargs.get('max_tokens') or 0), self._min_tokens)}
        for key in ('temperature', 'top_p', 'seed', 'stop'):
            if kwargs.get(key) is not None:
                payload[key] = kwargs[key]
        fmt = kwargs.get('response_format')
        if fmt and self._json_mode != 'none':
            payload['response_format'] = {'type': 'json_object'} if self._json_mode == 'json_object' else fmt
        if self._effort:
            payload['reasoning'] = {'effort': self._effort, 'exclude': True}
        return payload

    async def _create(self, **kwargs: Any) -> ChatCompletion:
        payload = self.build_payload(kwargs)
        self._roll()
        if self._used >= self._cap:
            raise DailyCapReached('local_daily_cap_reached')
        self._used += 1  # counted before the request: a failed call still used quota
        response = await self._http.post(self._base + '/chat/completions', json=payload,
                                         headers={'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json'})
        if response.status_code == 429:
            raise RateLimitError('openrouter rate limit', response=response, body=None)
        if response.status_code >= 400:
            raise APIStatusError('openrouter request failed', response=response, body=None)
        data = response.json()
        return ChatCompletion.model_validate(data)
