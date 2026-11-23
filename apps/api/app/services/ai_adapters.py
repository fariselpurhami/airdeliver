"""Thin adapters preserve current SDK/model/wire behavior and caller budgets."""
from typing import Any, Callable, Protocol
from app.core.ai_profile import AIProfile, UnsupportedAIProfile


class ChatAdapter(Protocol):
    def create_client(self, *, api_key: str, **options: Any) -> Any: ...


class GroqAdapter:
    def __init__(self, profile: AIProfile, sdk_factory: Callable[...,Any]):
        if profile.require('text') != 'groq' or profile.require('vision_understanding') != 'groq':
            raise UnsupportedAIProfile('Groq adapter capability mismatch')
        self.profile = profile
        self.sdk_factory = sdk_factory

    def create_client(self, *, api_key: str, **options: Any) -> Any:
        # Keep caller timeout and SDK defaults, including existing env routing.
        # Retry policy belongs to the service's single outer deadline.
        return self.sdk_factory(api_key=api_key, max_retries=0, **options)


class LocalRetrievalAdapter:
    def __init__(self, profile: AIProfile):
        profile.require('text_retrieval'); profile.require('image_retrieval')
        self.profile = profile

    def create_text_encoder(self, factory: Callable[...,Any], **options: Any) -> Any:
        return factory(self.profile.text_retrieval_model, **options)

    def create_image_component(self, factory: Callable[...,Any], **options: Any) -> Any:
        return factory(self.profile.image_retrieval_model, **options)


class ElevenLabsConversationAdapter:
    def __init__(self, profile: AIProfile):
        if profile.require('voice') != 'elevenlabs_conversation':
            raise UnsupportedAIProfile('Voice adapter capability mismatch')
        self.profile = profile

    async def connect(self, connector: Callable[...,Any], url: str, *, headers: dict,
                      ping_interval: int, ping_timeout: int) -> Any:
        # Existing VoiceConfig resolves agent/key; no new STT/TTS abstraction claim.
        return await connector(url, additional_headers=headers,
                               ping_interval=ping_interval, ping_timeout=ping_timeout)
