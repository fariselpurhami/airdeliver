"""Validated current AI profile. Selection is configuration, not live capability proof.

Only existing adapters are registered. New providers must implement and pass
contracts before a profile may select them. Retrieval identity is index-bound.
"""
from dataclasses import dataclass
import os
import re
from typing import Mapping
from app.core.catalog_contract import (PRODUCT_TEXT_MODEL_NAME, PRODUCT_TEXT_MODEL_DIMENSION,
                                       DEFAULT_PRODUCT_TEXT_MODEL_REVISION)


class UnsupportedAIProfile(ValueError):
    pass


@dataclass(frozen=True)
class AIProfile:
    name: str
    text_provider: str = 'groq'
    brain_model: str = 'openai/gpt-oss-120b'
    reflex_model: str = 'openai/gpt-oss-20b'
    support_model: str = 'llama-3.3-70b-versatile'
    vision_provider: str = 'groq'
    vision_model: str = 'qwen/qwen3.8-27b'
    text_retrieval_provider: str = 'local_sentence_transformer'
    text_retrieval_model: str = PRODUCT_TEXT_MODEL_NAME
    text_retrieval_dimension: int = PRODUCT_TEXT_MODEL_DIMENSION
    text_retrieval_revision: str = DEFAULT_PRODUCT_TEXT_MODEL_REVISION
    image_retrieval_provider: str = 'local_siglip'
    image_retrieval_model: str = 'google/siglip2-so400m-patch14-384'
    image_retrieval_dimension: int = 1152
    voice_provider: str = 'elevenlabs_conversation'
    voice_ws_template: str = 'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}'

    def require(self, capability: str) -> str:
        capabilities = {'text': self.text_provider, 'vision_understanding': self.vision_provider,
                        'text_retrieval': self.text_retrieval_provider,
                        'image_retrieval': self.image_retrieval_provider, 'voice': self.voice_provider}
        if capability not in capabilities:
            raise UnsupportedAIProfile('Unsupported AI capability; no silent fallback')
        return capabilities[capability]

    def __post_init__(self):
        expected = {'text_provider':'groq','vision_provider':'groq',
                    'text_retrieval_provider':'local_sentence_transformer',
                    'image_retrieval_provider':'local_siglip','voice_provider':'elevenlabs_conversation'}
        if any(getattr(self,key) != value for key,value in expected.items()):
            raise UnsupportedAIProfile('Unregistered AI provider adapter')
        for model in (self.brain_model,self.reflex_model,self.support_model,self.vision_model):
            if not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}',model):
                raise UnsupportedAIProfile('Invalid model identifier')
        if (self.text_retrieval_model != PRODUCT_TEXT_MODEL_NAME
                or self.text_retrieval_dimension != PRODUCT_TEXT_MODEL_DIMENSION
                or self.image_retrieval_model != 'google/siglip2-so400m-patch14-384'
                or self.image_retrieval_dimension != 1152):
            raise UnsupportedAIProfile('Retrieval profile change requires versioned index migration and evaluation')


def get_ai_profile(environ: Mapping[str,str] | None = None) -> AIProfile:
    env = os.environ if environ is None else environ
    name = env.get('AI_PROFILE','current-v1')
    if name != 'current-v1':
        raise UnsupportedAIProfile('Unknown AI_PROFILE; no implicit provider substitution')
    # Preserve existing role-specific model overrides. Support previously had no override.
    return AIProfile(name=name,
        brain_model=env.get('GROQ_BRAIN_MODEL','openai/gpt-oss-120b'),
        reflex_model=env.get('GROQ_MODEL','openai/gpt-oss-20b'),
        support_model=env.get('GROQ_SUPPORT_MODEL','llama-3.3-70b-versatile'),
        vision_model=env.get('GROQ_VISION_MODEL','qwen/qwen3.8-27b'))
