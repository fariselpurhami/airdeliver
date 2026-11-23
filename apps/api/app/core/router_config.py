"""Offline router config checks, never a provider health or access claim."""
import logging
import os
from dataclasses import dataclass
from urllib.parse import urlsplit
from app.core.ai_profile import get_ai_profile, UnsupportedAIProfile

logger=logging.getLogger('airdeliver.neural_core')
DEFAULT_GROQ_BASE_URL='https://api.groq.com'

class RouterConfigurationError(ValueError):
    pass

@dataclass(frozen=True)
class RouterConfig:
    model: str
    base_url: str


def get_router_config(environ=None):
    env=os.environ if environ is None else environ
    try:
        model=get_ai_profile(env).support_model
    except UnsupportedAIProfile:
        raise RouterConfigurationError('invalid_profile_or_model') from None
    raw=env.get('GROQ_BASE_URL',DEFAULT_GROQ_BASE_URL)
    try:
        url=urlsplit(raw)
        valid=(url.scheme=='https' and url.hostname and not url.username and not url.password
               and not url.query and not url.fragment and url.path in ('','/'))
        if not valid:raise ValueError()
        port=url.port
    except (TypeError,ValueError):
        # Never include the supplied URL, which could contain credentials.
        raise RouterConfigurationError('invalid_native_sdk_base_url') from None
    return RouterConfig(model=model,base_url=raw.rstrip('/'))


def log_router_configuration(environ=None):
    try:
        config=get_router_config(environ)
    except RouterConfigurationError as exc:
        logger.error('neural_core.config.invalid reason=%s',str(exc))
        return None
    logger.info('neural_core.config.validated provider=groq model=%s endpoint_kind=%s validation=offline_only',
                config.model,'groq_native' if config.base_url==DEFAULT_GROQ_BASE_URL else 'custom_native_root')
    if config.model in {'llama-3.3-70b-versatile','llama-3.1-8b-instant'}:
        logger.warning('neural_core.config.enterprise_model selected=explicit_override access_not_verified=true')
    return config
