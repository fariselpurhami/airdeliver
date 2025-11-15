# apps/api/app/core/config.py

import functools
from pydantic_settings import BaseSettings
from typing import List, Optional, Literal
from pydantic import computed_field, Field, ValidationError

class CoreSettings(BaseSettings):
    APP_ENV: Literal["development", "staging", "production"] = Field("production", env="APP_ENV")
    API_V1_STR: str = "/api/v1"
    API_BASE_URL: str = Field(..., env="API_BASE_URL")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    REFRESH_SECRET_KEY: str = Field(..., env="REFRESH_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    ALGORITHM: str = Field(..., env="ALGORITHM")
    COOKIES_SECURE: bool = False
    INTERNAL_API_TOKEN: str = Field(..., env="INTERNAL_API_TOKEN")
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")

    USE_REDIS: bool = Field(default=False, env="USE_REDIS")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")

    FIRST_SUPERUSER: str
    FIRST_SUPERUSER_PASSWORD: str
    RABBITMQ_USER: str = Field(..., env="RABBITMQ_USER")
    RABBITMQ_PASS: str = Field(..., env="RABBITMQ_PASS")
    RABBITMQ_HOST: str = Field(..., env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(..., env="RABBITMQ_PORT")
    DRONE_JWT_SECRET: str = Field(..., env="DRONE_JWT_SECRET")
    EXCHANGE_TELEMETRY: str = "drone.telemetry"
    EXCHANGE_EVENTS: str = "drone.events"
    EXCHANGE_COMMANDS: str = "drone.commands"
    QUEUE_TELEMETRY: str = "api.telemetry.processor"
    QUEUE_EVENTS: str = "api.events.processor"
    VAPID_PUBLIC_KEY: str
    VAPID_PRIVATE_KEY: str
    AI_CHAT_STATE_TTL_SECONDS: int = 900

    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:5432/{self.POSTGRES_DB}"

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @computed_field
    @property
    def REDIS_URL(self) -> Optional[str]:
        if not self.USE_REDIS:
            return None
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

class StripeSettings(BaseSettings):
    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    model_config = {"case_sensitive": True, "env_file": ".env", "extra": "ignore"}

class PayPalSettings(BaseSettings):
    PAYPAL_CLIENT_ID: str = Field(..., env="PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: str = Field(..., env="PAYPAL_CLIENT_SECRET")
    PAYPAL_API_BASE_URL: str = Field("https://api-m.sandbox.paypal.com", env="PAYPAL_API_BASE_URL")
    model_config = {"case_sensitive": True, "env_file": ".env", "extra": "ignore"}

class MpesaSettings(BaseSettings):
    MPESA_CONSUMER_KEY: str = Field(..., env="MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET: str = Field(..., env="MPESA_CONSUMER_SECRET")
    MPESA_API_BASE_URL: str = Field("https://sandbox.safaricom.co.ke", env="MPESA_API_BASE_URL")
    MPESA_SHORTCODE: str = Field(..., env="MPESA_SHORTCODE")
    MPESA_PASSKEY: str = Field(..., env="MPESA_PASSKEY")
    MPESA_CALLBACK_URL: str = Field(..., env="MPESA_CALLBACK_URL")
    model_config = {"case_sensitive": True, "env_file": ".env", "extra": "ignore"}

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
