# apps/api/app/core/config.py

import functools
import urllib.parse
from typing import List, Literal, Optional

from pydantic import AnyHttpUrl, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CoreSettings(BaseAppConfig):
    APP_ENV: Literal["development", "staging", "production"] = Field("production", alias="APP_ENV")
    API_V1_STR: str = "/api/v1"
    API_BASE_URL: AnyHttpUrl = Field(..., alias="API_BASE_URL")
    
    SECRET_KEY: SecretStr = Field(..., alias="SECRET_KEY", min_length=32)
    REFRESH_SECRET_KEY: SecretStr = Field(..., alias="REFRESH_SECRET_KEY", min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(11520, ge=1)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(10080, ge=1)
    ALGORITHM: str = Field(..., alias="ALGORITHM")
    COOKIES_SECURE: bool = Field(default=True, alias="COOKIES_SECURE")
    
    INTERNAL_API_TOKEN: SecretStr = Field(..., alias="INTERNAL_API_TOKEN")
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="BACKEND_CORS_ORIGINS"
    )

    POSTGRES_SERVER: str = Field(..., alias="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., alias="POSTGRES_USER")
    POSTGRES_PASSWORD: SecretStr = Field(..., alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., alias="POSTGRES_DB")

    USE_REDIS: bool = Field(default=False, alias="USE_REDIS")
    REDIS_HOST: str = Field(default="redis", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT", ge=1, le=65535)
    REDIS_PASSWORD: Optional[SecretStr] = Field(default=None, alias="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, alias="REDIS_DB", ge=0)

    FIRST_SUPERUSER: str = Field(..., alias="FIRST_SUPERUSER")
    FIRST_SUPERUSER_PASSWORD: SecretStr = Field(..., alias="FIRST_SUPERUSER_PASSWORD", min_length=8)
    
    RABBITMQ_USER: str = Field(..., alias="RABBITMQ_USER")
    RABBITMQ_PASS: SecretStr = Field(..., alias="RABBITMQ_PASS")
    RABBITMQ_HOST: str = Field(..., alias="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(5672, alias="RABBITMQ_PORT", ge=1, le=65535)
    
    DRONE_JWT_SECRET: SecretStr = Field(..., alias="DRONE_JWT_SECRET", min_length=32)
    
    EXCHANGE_TELEMETRY: str = "drone.telemetry"
    EXCHANGE_EVENTS: str = "drone.events"
    EXCHANGE_COMMANDS: str = "drone.commands"
    QUEUE_TELEMETRY: str = "api.telemetry.processor"
    QUEUE_EVENTS: str = "api.events.processor"
    
    VAPID_PUBLIC_KEY: str = Field(..., alias="VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY: SecretStr = Field(..., alias="VAPID_PRIVATE_KEY")
    
    AI_CHAT_STATE_TTL_SECONDS: int = Field(900, ge=60)
    EMBEDDING_MODEL_PATH: str = Field("all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_PATH")

    OPENSEARCH_HOST: str = Field("opensearch", alias="OPENSEARCH_HOST")
    OPENSEARCH_PORT: int = Field(9200, alias="OPENSEARCH_PORT", ge=1, le=65535)
    OPENSEARCH_USE_SSL: bool = Field(False, alias="OPENSEARCH_USE_SSL")
    OPENSEARCH_VERIFY_CERTS: bool = Field(False, alias="OPENSEARCH_VERIFY_CERTS")
    OPENSEARCH_USER: Optional[str] = Field(default=None, alias="OPENSEARCH_USER")
    OPENSEARCH_PASS: Optional[SecretStr] = Field(default=None, alias="OPENSEARCH_PASS")

    MILVUS_URI: AnyHttpUrl = Field(default=AnyHttpUrl("http://milvus:19530"), alias="MILVUS_URI")
    MILVUS_TOKEN: Optional[SecretStr] = Field(default=None, alias="MILVUS_TOKEN")

    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD.get_secret_value())
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        password = urllib.parse.quote_plus(self.RABBITMQ_PASS.get_secret_value())
        return f"amqp://{self.RABBITMQ_USER}:{password}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @computed_field
    @property
    def REDIS_URL(self) -> Optional[str]:
        if not self.USE_REDIS:
            return None
        
        auth_part = ""
        if self.REDIS_PASSWORD:
            password = urllib.parse.quote_plus(self.REDIS_PASSWORD.get_secret_value())
            auth_part = f":{password}@"
            
        return f"redis://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class StripeSettings(BaseAppConfig):
    STRIPE_SECRET_KEY: SecretStr = Field(..., alias="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: SecretStr = Field(..., alias="STRIPE_WEBHOOK_SECRET")
    STRIPE_PUBLISHABLE_KEY: str = Field(..., alias="STRIPE_PUBLISHABLE_KEY")


class PayPalSettings(BaseAppConfig):
    PAYPAL_CLIENT_ID: str = Field(..., alias="PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: SecretStr = Field(..., alias="PAYPAL_CLIENT_SECRET")
    PAYPAL_API_BASE_URL: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://api-m.sandbox.paypal.com"),
        alias="PAYPAL_API_BASE_URL"
    )


class MpesaSettings(BaseAppConfig):
    MPESA_CONSUMER_KEY: str = Field(..., alias="MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET: SecretStr = Field(..., alias="MPESA_CONSUMER_SECRET")
    MPESA_API_BASE_URL: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://sandbox.safaricom.co.ke"),
        alias="MPESA_API_BASE_URL"
    )
    MPESA_SHORTCODE: str = Field(..., alias="MPESA_SHORTCODE")
    MPESA_PASSKEY: SecretStr = Field(..., alias="MPESA_PASSKEY")
    MPESA_CALLBACK_URL: AnyHttpUrl = Field(..., alias="MPESA_CALLBACK_URL")


@functools.lru_cache()
def get_core_settings() -> CoreSettings:
    return CoreSettings()


@functools.lru_cache()
def get_stripe_settings() -> StripeSettings:
    return StripeSettings()


@functools.lru_cache()
def get_paypal_settings() -> PayPalSettings:
    return PayPalSettings()


@functools.lru_cache()
def get_mpesa_settings() -> MpesaSettings:
    return MpesaSettings()


settings = get_core_settings()
