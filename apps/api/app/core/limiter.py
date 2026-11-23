# file: apps/api/app/core/limiter.py
"""Shared HTTP limits. Forwarded headers are never trusted by this module."""
from fastapi import Request
from fastapi.responses import JSONResponse
from limits.errors import StorageError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIASGIMiddleware
from app.core.config import get_core_settings


def build_limiter(settings):
    # Existing Redis infrastructure only. Memory mode is explicit via USE_REDIS=false.
    # Fail closed on Redis errors; never silently split shared quotas by worker.
    return Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT],
                   storage_uri=settings.REDIS_URL or 'memory://',
                   key_prefix='airdeliver:http',
                   storage_options={'socket_connect_timeout':0.25,'socket_timeout':0.25,
                                    'wrap_exceptions':True} if settings.USE_REDIS else {},
                   swallow_errors=False, in_memory_fallback_enabled=False)


limiter = build_limiter(get_core_settings())


def storage_unavailable(request: Request, exc: StorageError):
    # Do not echo storage URLs, credentials or backend exception text.
    return JSONResponse(status_code=503,content={'detail':'Rate limit storage unavailable'},
                        headers={'Retry-After':'1'})


def install_rate_limiting(app, instance=None):
    app.state.limiter = instance if instance is not None else limiter
    app.add_exception_handler(StorageError, storage_unavailable)
    app.add_middleware(SlowAPIASGIMiddleware)
